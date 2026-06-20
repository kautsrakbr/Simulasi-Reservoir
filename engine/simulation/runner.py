from __future__ import annotations

from typing import TypedDict

from engine.domain.grid import GridModel
from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult, StepAttempt, TimeStepResult
from engine.domain.state import ReservoirState
from engine.grid.builder import build_grid
from engine.numerics.jacobian_fd import assemble_jacobian_fd
from engine.physics.accumulation import assemble_accumulation_terms
from engine.physics.flux import compute_phase_connection_fluxes, compute_phase_net_flux_per_cell
from engine.physics.residual import assemble_full_residual, residual_max_abs
from engine.physics.transmissibility import update_grid_transmissibility
from engine.reporting.result_builder import build_run_result, build_step_result
from engine.simulation.initializer import initialize_state
from engine.simulation.newton import newton_step
from engine.simulation.timestep import accept_timestep, reject_timestep, update_timestep


def _copy_state(state: ReservoirState) -> ReservoirState:
	return ReservoirState(
		pressure=list(state.pressure),
		sw=list(state.sw),
		sg=list(state.sg),
	)


def _clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def _compute_mean_transmissibility(grid_model: GridModel) -> float:
	if not grid_model.connections:
		return 0.0
	return sum(connection.transmissibility for connection in grid_model.connections) / len(grid_model.connections)


class _StepDiagnostics(TypedDict):
	connection_fluxes: list[float]
	net_flux: list[float]
	phase_net_flux_oil: list[float]
	phase_net_flux_water: list[float]
	phase_net_flux_gas: list[float]
	oil_residual_per_cell: list[float]
	water_residual_per_cell: list[float]
	gas_residual_per_cell: list[float]
	max_oil_residual: float
	max_water_residual: float
	max_gas_residual: float
	residual_vector: list[float]
	accumulation_total: list[float]
	residual_per_cell: list[float]
	max_residual: float
	max_residual_vector: float
	max_connection_flux: float
	max_abs_accumulation: float
	residual_norm: float
	residual_norm_vector: float


def _compute_step_diagnostics(
	project_config: ProjectConfig,
	grid_model: GridModel,
	previous_state: ReservoirState,
	current_state: ReservoirState,
	dt_days: float,
) -> _StepDiagnostics:
	phase_connection_fluxes = compute_phase_connection_fluxes(
		grid_model,
		current_state,
		reference_data=project_config.reference_data,
		pvt_tables=project_config.pvt_tables,
		rock_tables=project_config.rock_tables,
	)
	phase_flux = compute_phase_net_flux_per_cell(grid_model, phase_connection_fluxes)
	net_flux = [
		oil + water + gas
		for oil, water, gas in zip(
			phase_flux["oil"],
			phase_flux["water"],
			phase_flux["gas"],
		)
	]
	connection_fluxes = [
		oil + water + gas
		for oil, water, gas in zip(
			phase_connection_fluxes["oil"],
			phase_connection_fluxes["water"],
			phase_connection_fluxes["gas"],
		)
	]
	accumulation_terms = assemble_accumulation_terms(
		grid_model,
		previous_state,
		current_state,
		project_config.reference_data,
		project_config.pvt_tables,
		dt_days,
	)
	accumulation_total = accumulation_terms["total"]
	oil_residual_per_cell = assemble_full_residual(phase_flux["oil"], accumulation_terms["oil"])
	water_residual_per_cell = assemble_full_residual(phase_flux["water"], accumulation_terms["water"])
	gas_residual_per_cell = assemble_full_residual(phase_flux["gas"], accumulation_terms["gas"])
	max_oil_residual = residual_max_abs(oil_residual_per_cell)
	max_water_residual = residual_max_abs(water_residual_per_cell)
	max_gas_residual = residual_max_abs(gas_residual_per_cell)
	residual_per_cell = assemble_full_residual(net_flux, accumulation_total)
	residual_vector = oil_residual_per_cell + water_residual_per_cell + gas_residual_per_cell
	max_residual = residual_max_abs(residual_per_cell)
	max_residual_vector = residual_max_abs(residual_vector)
	max_connection_flux = max((abs(value) for value in connection_fluxes), default=0.0)
	max_abs_accumulation = max(
		(
			abs(value)
			for values in (accumulation_terms["oil"], accumulation_terms["water"], accumulation_terms["gas"])
			for value in values
		),
		default=0.0,
	)
	max_abs_phase_flux = max(
		(
			abs(value)
			for values in (phase_flux["oil"], phase_flux["water"], phase_flux["gas"])
			for value in values
		),
		default=0.0,
	)
	reference_scale = max(max_connection_flux, max_abs_phase_flux, max_abs_accumulation, 1.0)
	residual_norm = max_residual / reference_scale
	residual_norm_vector = max_residual_vector / reference_scale
	return {
		"connection_fluxes": connection_fluxes,
		"net_flux": net_flux,
		"phase_net_flux_oil": phase_flux["oil"],
		"phase_net_flux_water": phase_flux["water"],
		"phase_net_flux_gas": phase_flux["gas"],
		"oil_residual_per_cell": oil_residual_per_cell,
		"water_residual_per_cell": water_residual_per_cell,
		"gas_residual_per_cell": gas_residual_per_cell,
		"max_oil_residual": max_oil_residual,
		"max_water_residual": max_water_residual,
		"max_gas_residual": max_gas_residual,
		"residual_vector": residual_vector,
		"accumulation_total": accumulation_total,
		"residual_per_cell": residual_per_cell,
		"max_residual": max_residual,
		"max_residual_vector": max_residual_vector,
		"max_connection_flux": max_connection_flux,
		"max_abs_accumulation": max_abs_accumulation,
		"residual_norm": residual_norm,
		"residual_norm_vector": residual_norm_vector,
	}


def _apply_pressure_relaxation(current_state: ReservoirState, residual_per_cell: list[float]) -> ReservoirState:
	if not residual_per_cell:
		return _copy_state(current_state)

	pressure = list(current_state.pressure)
	for index, pressure_value in enumerate(pressure):
		residual_value = residual_per_cell[index] if index < len(residual_per_cell) else 0.0
		pressure[index] = max(14.7, pressure_value - 0.02 * residual_value)

	return ReservoirState(pressure=pressure, sw=list(current_state.sw), sg=list(current_state.sg))


def _initialize_iteration_state(previous_state: ReservoirState) -> ReservoirState:
	pressure = [max(14.7, value - 2.0) for value in previous_state.pressure]
	return ReservoirState(pressure=pressure, sw=list(previous_state.sw), sg=list(previous_state.sg))


def run_simulation(project_config: ProjectConfig) -> RunResult:
	grid_model = build_grid(project_config)
	committed_state = initialize_state(project_config, grid_model)
	update_grid_transmissibility(grid_model)
	mean_transmissibility = _compute_mean_transmissibility(grid_model)

	time_days = 0.0
	dt_days = max(project_config.solver.initial_timestep_days, 1e-6)
	max_time_days = max(project_config.solver.max_time_days, dt_days)
	steps = []
	warnings: list[str] = []
	step_guard = 0
	min_dt_days = max(project_config.solver.min_timestep_days, 1e-6)
	max_step_retries = max(project_config.solver.max_step_retries, 0)
	shrink_factor = min(max(project_config.solver.timestep_shrink_factor, 1e-6), 0.999999)
	growth_factor = max(project_config.solver.timestep_growth_factor, 1.0)

	while time_days < max_time_days - 1e-12:
		step_guard += 1
		if step_guard > 1000:
			warnings.append("Loop timestep dihentikan karena melewati batas safety guard.")
			break

		remaining_time = max_time_days - time_days
		trial_dt = min(dt_days, remaining_time)
		accepted = False
		step_attempts: list[StepAttempt] = []

		for retry_index in range(max_step_retries + 1):
			next_time_days = time_days + trial_dt
			step_result, next_state, converged, residual_norm = run_timestep(
				project_config,
				grid_model,
				committed_state,
				trial_dt,
				next_time_days,
				mean_transmissibility,
			)
			step_attempts.append(
				StepAttempt(
					retry_index=retry_index,
					target_time_days=next_time_days,
					dt_days=trial_dt,
					converged=converged,
					max_residual=step_result.summary.max_residual,
					residual_norm=residual_norm,
					note="accepted" if converged else "retry",
				)
			)
			step_result.attempts = list(step_attempts)

			if converged:
				steps.append(step_result)
				committed_state = commit_timestep_state(next_state)
				time_days = accept_timestep(time_days, trial_dt)
				dt_days = update_timestep(trial_dt, growth_factor=growth_factor)
				accepted = True
				break

			reduced_dt = reject_timestep(trial_dt, shrink_factor=shrink_factor)
			warnings.append(
				f"Step t={next_time_days:.2f} hari gagal konvergen pada dt={trial_dt:.4f}; retry dengan dt={reduced_dt:.4f}."
			)
			if retry_index >= max_step_retries or reduced_dt < min_dt_days:
				if step_result.attempts:
					step_result.attempts[-1].note = "abort-min-dt"
				steps.append(step_result)
				warnings.append(
					"Simulasi dihentikan karena step tidak konvergen dan dt minimum tercapai."
				)
				return build_run_result(
					case_name=project_config.run.case_name,
					steps=steps,
					warnings=warnings,
				)
			trial_dt = min(reduced_dt, remaining_time)

		if not accepted:
			break

	return build_run_result(case_name=project_config.run.case_name, steps=steps, warnings=warnings)


def run_timestep(
	project_config: ProjectConfig,
	grid_model: GridModel,
	previous_state: ReservoirState,
	dt_days: float,
	time_days: float,
	mean_transmissibility: float,
) -> tuple[TimeStepResult, ReservoirState, bool, float]:
	working_state = _initialize_iteration_state(previous_state)
	max_iterations = max(1, project_config.solver.max_newton_iterations)
	# Newton stops as soon as the max normalised residual drops to/below this tolerance
	# (configured via "Residual Tolerance" in Model & Solver); otherwise it keeps iterating.
	residual_target = project_config.solver.residual_tolerance

	final_diagnostics: _StepDiagnostics | None = None
	used_iterations = 0
	converged = False

	last_jacobian: list[list[float]] = []
	corrections_history: list[list[float]] = []

	for iteration in range(1, max_iterations + 1):
		used_iterations = iteration
		final_diagnostics = _compute_step_diagnostics(
			project_config,
			grid_model,
			previous_state,
			working_state,
			dt_days,
		)

		if float(final_diagnostics["residual_norm_vector"]) <= residual_target:
			converged = True
			break
		# residual still above tolerance → keep iterating until max_newton_iterations

		def _residual_evaluator(candidate_state: ReservoirState) -> list[float]:
			candidate_diagnostics = _compute_step_diagnostics(
				project_config,
				grid_model,
				previous_state,
				candidate_state,
				dt_days,
			)
			return list(candidate_diagnostics["residual_vector"])

		try:
			residual_vector = list(final_diagnostics["residual_vector"])
			jacobian = assemble_jacobian_fd(
				working_state,
				_residual_evaluator,
				pressure_delta=1e-6,
				sw_delta=1e-6,
				sg_delta=1e-6,
				unknown_layout="pressure_sw_sg",
			)
			last_jacobian = jacobian
			working_state, correction = newton_step(
				working_state,
				residual_vector,
				jacobian,
				project_config.solver,
			)
			corrections_history.append(list(correction))
		except ValueError:
			working_state = _apply_pressure_relaxation(
				working_state,
				list(final_diagnostics["residual_per_cell"]),
			)

	if final_diagnostics is None:
		final_diagnostics = _compute_step_diagnostics(
			project_config,
			grid_model,
			previous_state,
			working_state,
			dt_days,
		)

	step_result = build_step_result(
		time_days=time_days,
		newton_iterations=used_iterations,
		max_residual=float(final_diagnostics["max_residual"]),
		converged=converged,
	)
	step_result.jacobian = last_jacobian
	step_result.corrections = corrections_history
	step_result.pressure = working_state.pressure
	step_result.sw = working_state.sw
	step_result.sg = working_state.sg
	step_result.so = [_clamp(1.0 - sw - sg, 0.0, 1.0) for sw, sg in zip(working_state.sw, working_state.sg)]
	step_result.connection_fluxes = final_diagnostics["connection_fluxes"]
	step_result.net_flux_per_cell = final_diagnostics["net_flux"]
	step_result.mean_transmissibility = mean_transmissibility
	step_result.max_connection_flux = float(final_diagnostics["max_connection_flux"])
	step_result.max_abs_accumulation = float(final_diagnostics["max_abs_accumulation"])
	step_result.accumulation_per_cell = final_diagnostics["accumulation_total"]
	step_result.residual_per_cell = final_diagnostics["residual_per_cell"]
	step_result.oil_residual_per_cell = final_diagnostics["oil_residual_per_cell"]
	step_result.water_residual_per_cell = final_diagnostics["water_residual_per_cell"]
	step_result.gas_residual_per_cell = final_diagnostics["gas_residual_per_cell"]
	step_result.max_oil_residual = float(final_diagnostics["max_oil_residual"])
	step_result.max_water_residual = float(final_diagnostics["max_water_residual"])
	step_result.max_gas_residual = float(final_diagnostics["max_gas_residual"])
	residual_norm = float(final_diagnostics["residual_norm"])
	return step_result, working_state, converged, residual_norm


def commit_timestep_state(state: ReservoirState) -> ReservoirState:
	return _copy_state(state)


def emit_progress(message: str) -> str:
	return message

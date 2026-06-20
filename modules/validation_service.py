from __future__ import annotations

from engine.domain.project import ProjectConfig


def validate_project(project_config: ProjectConfig) -> list[str]:
	errors: list[str] = []
	errors.extend(validate_grid_inputs(project_config))
	errors.extend(validate_solver_inputs(project_config))
	errors.extend(validate_pvt_inputs(project_config))
	errors.extend(validate_rock_inputs(project_config))
	errors.extend(validate_initial_state(project_config))
	return errors


def validate_grid_inputs(project_config: ProjectConfig) -> list[str]:
	errors: list[str] = []
	if project_config.grid_spec.nx <= 0:
		errors.append("Grid nx harus lebih besar dari 0.")
	if project_config.grid_spec.ny <= 0:
		errors.append("Grid ny harus lebih besar dari 0.")
	if project_config.grid_spec.nz <= 0:
		errors.append("Grid nz harus lebih besar dari 0.")
	return errors


def validate_solver_inputs(project_config: ProjectConfig) -> list[str]:
	errors: list[str] = []
	if project_config.solver.initial_timestep_days <= 0.0:
		errors.append("Initial timestep harus lebih besar dari 0.")
	if project_config.solver.min_timestep_days <= 0.0:
		errors.append("Min timestep harus lebih besar dari 0.")
	if project_config.solver.max_time_days <= 0.0:
		errors.append("Max time harus lebih besar dari 0.")
	if project_config.solver.timestep_growth_factor < 1.0:
		errors.append("Timestep growth factor minimal 1.0.")
	if not 0.0 < project_config.solver.timestep_shrink_factor < 1.0:
		errors.append("Timestep shrink factor harus berada di antara 0 dan 1.")
	if project_config.solver.max_step_retries < 0:
		errors.append("Max step retries tidak boleh negatif.")
	if project_config.solver.max_newton_iterations < 1:
		errors.append("Max Newton iterations minimal 1.")
	if project_config.solver.residual_tolerance <= 0.0:
		errors.append("Residual tolerance harus lebih besar dari 0.")
	if project_config.solver.residual_norm_floor <= 0.0:
		errors.append("Residual norm floor harus lebih besar dari 0.")
	if project_config.solver.parameter_tolerance_pressure <= 0.0:
		errors.append("Parameter tolerance (Δp) harus lebih besar dari 0.")
	if project_config.solver.parameter_tolerance_saturation <= 0.0:
		errors.append("Parameter tolerance (ΔS) harus lebih besar dari 0.")
	if not 0.0 < project_config.solver.newton_pressure_damping <= 1.0:
		errors.append("Newton pressure damping harus berada pada rentang (0, 1].")
	if not 0.0 < project_config.solver.newton_saturation_damping <= 1.0:
		errors.append("Newton saturation damping harus berada pada rentang (0, 1].")
	if project_config.solver.max_pressure_correction <= 0.0:
		errors.append("Max pressure correction harus lebih besar dari 0.")
	if project_config.solver.max_saturation_correction <= 0.0:
		errors.append("Max saturation correction harus lebih besar dari 0.")
	if project_config.solver.max_saturation_correction > 1.0:
		errors.append("Max saturation correction tidak boleh lebih besar dari 1.")
	if project_config.solver.min_timestep_days > project_config.solver.initial_timestep_days:
		errors.append("Min timestep tidak boleh lebih besar dari initial timestep.")
	if project_config.solver.max_time_days < project_config.solver.initial_timestep_days:
		errors.append("Max time harus lebih besar atau sama dengan initial timestep.")
	return errors


def validate_pvt_inputs(project_config: ProjectConfig) -> list[str]:
	if project_config.pvt_tables:
		return []
	return ["Data PVT belum diisi."]


def validate_rock_inputs(project_config: ProjectConfig) -> list[str]:
	if project_config.rock_tables:
		return []
	return ["Data rock-fluid belum diisi."]


def validate_initial_state(project_config: ProjectConfig) -> list[str]:
	errors: list[str] = []
	if project_config.reference_data.reference_pressure <= 0.0:
		errors.append("Reference pressure harus lebih besar dari 0.")
	if project_config.initial_conditions.reference_depth < 0.0:
		errors.append("Reference depth tidak boleh negatif.")
	if not 0.0 <= project_config.initial_conditions.initial_sw <= 1.0:
		errors.append("Initial Sw harus berada pada rentang 0 sampai 1.")
	if not 0.0 <= project_config.initial_conditions.initial_sg <= 1.0:
		errors.append("Initial Sg harus berada pada rentang 0 sampai 1.")
	if project_config.initial_conditions.initial_sw + project_config.initial_conditions.initial_sg > 1.0:
		errors.append("Jumlah initial Sw dan Sg tidak boleh lebih besar dari 1.")
	return errors

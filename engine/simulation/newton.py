from __future__ import annotations

from engine.domain.project import SolverConfig
from engine.domain.state import ReservoirState
from engine.numerics.linear_solver import solve_linear_system


def newton_step(
	state_k: ReservoirState,
	residual: list[float],
	jacobian: list[list[float]],
	solver_config: SolverConfig,
) -> tuple[ReservoirState, list[float]]:
	rhs = build_newton_rhs(residual)
	correction = solve_linear_system(jacobian, rhs, solver_config)
	return apply_newton_update(state_k, correction, solver_config), correction



def build_newton_rhs(residual: list[float]) -> list[float]:
	return [-value for value in residual]


def apply_newton_update(
	state_k: ReservoirState,
	correction: list[float],
	solver_config: SolverConfig,
) -> ReservoirState:
	pressure_damping = solver_config.newton_pressure_damping
	saturation_damping = solver_config.newton_saturation_damping
	max_delta = max(solver_config.max_pressure_correction, solver_config.parameter_tolerance)
	max_sat_delta = min(1.0, max(solver_config.max_saturation_correction, solver_config.parameter_tolerance))
	cell_count = len(state_k.pressure)
	new_pressure = list(state_k.pressure)
	for index, pressure in enumerate(new_pressure):
		delta = correction[index] if index < len(correction) else 0.0
		delta = max(-max_delta, min(max_delta, delta))
		new_pressure[index] = max(14.7, pressure + pressure_damping * delta)

	new_sw = list(state_k.sw)
	new_sg = list(state_k.sg)
	for index in range(cell_count):
		sw_delta_index = cell_count + index
		sg_delta_index = (2 * cell_count) + index
		delta_sw = correction[sw_delta_index] if sw_delta_index < len(correction) else 0.0
		delta_sg = correction[sg_delta_index] if sg_delta_index < len(correction) else 0.0
		delta_sw = max(-max_sat_delta, min(max_sat_delta, delta_sw))
		delta_sg = max(-max_sat_delta, min(max_sat_delta, delta_sg))
		sw_value = max(0.0, min(1.0, state_k.sw[index] + saturation_damping * delta_sw))
		sg_value = max(0.0, min(1.0, state_k.sg[index] + saturation_damping * delta_sg))
		if sw_value + sg_value > 1.0:
			total = sw_value + sg_value
			sw_value /= total
			sg_value /= total
		new_sw[index] = sw_value
		new_sg[index] = sg_value

	return ReservoirState(
		pressure=new_pressure,
		sw=new_sw,
		sg=new_sg,
	)

from __future__ import annotations

from collections.abc import Callable

from engine.domain.state import ReservoirState


def _copy_state(state: ReservoirState) -> ReservoirState:
	return ReservoirState(
		pressure=list(state.pressure),
		sw=list(state.sw),
		sg=list(state.sg),
	)


def _safe_delta(value: float, requested_delta: float) -> float:
	scale = max(abs(value), 1.0)
	return requested_delta * scale


def assemble_jacobian_fd(
	state_k: ReservoirState,
	residual_evaluator: Callable[[ReservoirState], list[float]],
	pressure_delta: float = 1e-6,
	sw_delta: float = 1e-6,
	sg_delta: float = 1e-6,
	unknown_layout: str = "pressure",
) -> list[list[float]]:
	base_residual = residual_evaluator(state_k)
	cell_count = len(state_k.pressure)
	if unknown_layout == "pressure_sw_sg":
		size = cell_count * 3
	else:
		size = len(base_residual)
	jacobian = [[0.0 for _ in range(size)] for _ in range(size)]

	if size == 0:
		return jacobian

	for column in range(size):
		if unknown_layout == "pressure_sw_sg":
			if column < cell_count:
				perturbed_state = perturb_pressure(state_k, column, pressure_delta)
				delta = perturbed_state.pressure[column] - state_k.pressure[column]
			elif column < 2 * cell_count:
				sw_index = column - cell_count
				perturbed_state = perturb_sw(state_k, sw_index, sw_delta)
				delta = perturbed_state.sw[sw_index] - state_k.sw[sw_index]
			else:
				sg_index = column - (2 * cell_count)
				perturbed_state = perturb_sg(state_k, sg_index, sg_delta)
				delta = perturbed_state.sg[sg_index] - state_k.sg[sg_index]
		else:
			perturbed_state = perturb_pressure(state_k, column, pressure_delta)
			if column < len(state_k.pressure):
				delta = perturbed_state.pressure[column] - state_k.pressure[column]
			else:
				delta = pressure_delta

		perturbed_residual = residual_evaluator(perturbed_state)
		if abs(delta) < 1e-20:
			delta = pressure_delta if column < cell_count else sw_delta
		for row in range(size):
			base_value = base_residual[row] if row < len(base_residual) else 0.0
			perturbed_value = perturbed_residual[row] if row < len(perturbed_residual) else base_value
			jacobian[row][column] = (perturbed_value - base_value) / delta

	return jacobian


def perturb_pressure(state_k: ReservoirState, cell_index: int, delta: float) -> ReservoirState:
	perturbed_state = _copy_state(state_k)
	if 0 <= cell_index < len(perturbed_state.pressure):
		actual_delta = _safe_delta(perturbed_state.pressure[cell_index], delta)
		perturbed_state.pressure[cell_index] += actual_delta
	return perturbed_state


def perturb_sw(state_k: ReservoirState, cell_index: int, delta: float) -> ReservoirState:
	perturbed_state = _copy_state(state_k)
	if 0 <= cell_index < len(perturbed_state.sw):
		actual_delta = _safe_delta(perturbed_state.sw[cell_index], delta)
		perturbed_state.sw[cell_index] = max(0.0, min(1.0, perturbed_state.sw[cell_index] + actual_delta))
	return perturbed_state


def perturb_sg(state_k: ReservoirState, cell_index: int, delta: float) -> ReservoirState:
	perturbed_state = _copy_state(state_k)
	if 0 <= cell_index < len(perturbed_state.sg):
		actual_delta = _safe_delta(perturbed_state.sg[cell_index], delta)
		perturbed_state.sg[cell_index] = max(0.0, min(1.0, perturbed_state.sg[cell_index] + actual_delta))
	return perturbed_state

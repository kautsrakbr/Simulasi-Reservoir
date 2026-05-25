from __future__ import annotations


def compute_residual_error(residual: list[float]) -> float:
	if not residual:
		return 0.0
	return max(abs(value) for value in residual)


def is_converged(residual: list[float], tolerance: float) -> bool:
	return compute_residual_error(residual) <= tolerance

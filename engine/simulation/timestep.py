from __future__ import annotations


def accept_timestep(time_days: float, dt_days: float) -> float:
	return time_days + dt_days


def reject_timestep(dt_days: float, shrink_factor: float = 0.5) -> float:
	return dt_days * shrink_factor


def update_timestep(dt_days: float, growth_factor: float = 1.0) -> float:
	return dt_days * growth_factor

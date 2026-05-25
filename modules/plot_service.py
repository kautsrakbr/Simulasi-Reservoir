from __future__ import annotations

from engine.domain.results import RunResult


def build_residual_series(run_result: RunResult) -> list[tuple[float, float]]:
	return [
		(step.summary.time_days, step.summary.max_residual)
		for step in run_result.steps
	]


def build_pressure_series(run_result: RunResult) -> list[tuple[float, float]]:
	series: list[tuple[float, float]] = []
	for step in run_result.steps:
		if not step.pressure:
			continue
		series.append((step.summary.time_days, step.pressure[0]))
	return series

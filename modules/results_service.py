from __future__ import annotations

from engine.domain.results import RunResult, TimeStepResult
from engine.reporting.summary import build_run_summary


def get_run_summary(run_result: RunResult) -> dict[str, float | int | bool]:
	return build_run_summary(run_result)


def get_latest_step(run_result: RunResult) -> TimeStepResult | None:
	if not run_result.steps:
		return None
	return run_result.steps[-1]

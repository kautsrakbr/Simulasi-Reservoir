from __future__ import annotations

from engine.domain.results import RunResult


def build_run_summary(run_result: RunResult) -> dict[str, float | int | bool]:
	if not run_result.steps:
		return {
			"step_count": 0,
			"final_time_days": 0.0,
			"last_max_residual": 0.0,
			"last_converged": False,
		}

	last_step = run_result.steps[-1]
	return {
		"step_count": len(run_result.steps),
		"final_time_days": last_step.summary.time_days,
		"last_max_residual": last_step.summary.max_residual,
		"last_converged": last_step.summary.converged,
	}

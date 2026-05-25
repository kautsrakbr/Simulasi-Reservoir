from __future__ import annotations

from engine.domain.results import RunResult


def build_run_summary(run_result: RunResult) -> dict[str, float | int | bool]:
	if not run_result.steps:
		return {
			"step_count": 0,
			"final_time_days": 0.0,
			"last_max_residual": 0.0,
			"last_max_oil_residual": 0.0,
			"last_max_water_residual": 0.0,
			"last_max_gas_residual": 0.0,
			"last_mean_transmissibility": 0.0,
			"last_max_connection_flux": 0.0,
			"last_max_abs_accumulation": 0.0,
			"retry_attempt_count": 0,
			"rejected_attempt_count": 0,
			"last_converged": False,
		}

	total_attempts = 0
	total_rejected_attempts = 0
	for step in run_result.steps:
		total_attempts += len(step.attempts)
		total_rejected_attempts += sum(1 for attempt in step.attempts if not attempt.converged)

	last_step = run_result.steps[-1]
	return {
		"step_count": len(run_result.steps),
		"final_time_days": last_step.summary.time_days,
		"last_max_residual": last_step.summary.max_residual,
		"last_max_oil_residual": last_step.max_oil_residual,
		"last_max_water_residual": last_step.max_water_residual,
		"last_max_gas_residual": last_step.max_gas_residual,
		"last_mean_transmissibility": last_step.mean_transmissibility,
		"last_max_connection_flux": last_step.max_connection_flux,
		"last_max_abs_accumulation": last_step.max_abs_accumulation,
		"retry_attempt_count": total_attempts,
		"rejected_attempt_count": total_rejected_attempts,
		"last_converged": last_step.summary.converged,
	}

from __future__ import annotations

from engine.domain.results import RunResult, StepSummary, TimeStepResult


def build_step_result(
	*,
	time_days: float,
	newton_iterations: int,
	max_residual: float,
	converged: bool,
) -> TimeStepResult:
	return TimeStepResult(
		summary=StepSummary(
			time_days=time_days,
			newton_iterations=newton_iterations,
			max_residual=max_residual,
			converged=converged,
		)
	)


def build_run_result(
	case_name: str,
	steps: list[TimeStepResult] | None = None,
	warnings: list[str] | None = None,
	total_elapsed_seconds: float = 0.0,
) -> RunResult:
	return RunResult(
		case_name=case_name,
		steps=steps or [],
		warnings=warnings or [],
		total_elapsed_seconds=total_elapsed_seconds,
	)

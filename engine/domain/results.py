from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class StepSummary:
	time_days: float = 0.0
	newton_iterations: int = 0
	max_residual: float = 0.0
	converged: bool = False


@dataclass(slots=True)
class TimeStepResult:
	summary: StepSummary = field(default_factory=StepSummary)
	pressure: list[float] = field(default_factory=list)
	sw: list[float] = field(default_factory=list)
	sg: list[float] = field(default_factory=list)
	so: list[float] = field(default_factory=list)


@dataclass(slots=True)
class RunResult:
	case_name: str = "Base Case"
	steps: list[TimeStepResult] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)

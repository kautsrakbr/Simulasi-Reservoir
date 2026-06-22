from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class StepSummary:
	time_days: float = 0.0
	newton_iterations: int = 0
	max_residual: float = 0.0
	converged: bool = False


@dataclass(slots=True)
class StepAttempt:
	retry_index: int = 0
	target_time_days: float = 0.0
	dt_days: float = 0.0
	converged: bool = False
	max_residual: float = 0.0
	residual_norm: float = 0.0
	note: str = ""


@dataclass(slots=True)
class TimeStepResult:
	summary: StepSummary = field(default_factory=StepSummary)
	attempts: list[StepAttempt] = field(default_factory=list)
	pressure: list[float] = field(default_factory=list)
	sw: list[float] = field(default_factory=list)
	sg: list[float] = field(default_factory=list)
	so: list[float] = field(default_factory=list)
	connection_fluxes: list[float] = field(default_factory=list)
	net_flux_per_cell: list[float] = field(default_factory=list)
	mean_transmissibility: float = 0.0
	max_connection_flux: float = 0.0
	max_abs_accumulation: float = 0.0
	accumulation_per_cell: list[float] = field(default_factory=list)
	residual_per_cell: list[float] = field(default_factory=list)
	oil_residual_per_cell: list[float] = field(default_factory=list)
	water_residual_per_cell: list[float] = field(default_factory=list)
	gas_residual_per_cell: list[float] = field(default_factory=list)
	max_oil_residual: float = 0.0
	max_water_residual: float = 0.0
	max_gas_residual: float = 0.0
	jacobian: list[list[float]] = field(default_factory=list)
	corrections: list[list[float]] = field(default_factory=list)



@dataclass(slots=True)
class RunResult:
	case_name: str = "Base Case"
	steps: list[TimeStepResult] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)
	total_elapsed_seconds: float = 0.0

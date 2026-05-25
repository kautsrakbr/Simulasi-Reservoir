from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScheduleStep:
	time_days: float = 0.0
	controls: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class Schedule:
	steps: list[ScheduleStep] = field(default_factory=list)

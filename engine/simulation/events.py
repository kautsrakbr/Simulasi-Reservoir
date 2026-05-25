from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationEvent:
	message: str
	level: str = "info"

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PVTPoint:
	pressure: float = 0.0
	bo: float = 0.0
	bw: float = 0.0
	bg: float = 0.0
	mu_o: float = 0.0
	mu_w: float = 0.0
	mu_g: float = 0.0
	rso: float = 0.0
	rsw: float = 0.0


@dataclass(slots=True)
class PVTTable:
	name: str = "default"
	points: list[PVTPoint] = field(default_factory=list)

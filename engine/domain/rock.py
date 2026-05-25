from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RelativePermeabilityPoint:
	sw: float = 0.0
	sg: float = 0.0
	kro: float = 0.0
	krw: float = 0.0
	krg: float = 0.0
	pcow: float = 0.0
	pcgw: float = 0.0


@dataclass(slots=True)
class RockFluidTable:
	name: str = "default"
	points: list[RelativePermeabilityPoint] = field(default_factory=list)

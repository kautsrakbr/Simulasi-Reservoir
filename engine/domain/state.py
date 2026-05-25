from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(slots=True)
class ReservoirState:
	pressure: list[float] = field(default_factory=list)
	sw: list[float] = field(default_factory=list)
	sg: list[float] = field(default_factory=list)

@dataclass(slots=True)
class IterationState:
	iteration: int = 0
	pressure: list[float] = field(default_factory=list)
	sw: list[float] = field(default_factory=list)
	sg: list[float] = field(default_factory=list)
	so: list[float] = field(default_factory=list)

@dataclass(slots=True)
class CellPVTProperties:
	bo: list[float] = field(default_factory=list)
	bw: list[float] = field(default_factory=list)
	bg: list[float] = field(default_factory=list)
	mu_o: list[float] = field(default_factory=list)
	mu_w: list[float] = field(default_factory=list)
	mu_g: list[float] = field(default_factory=list)
	rso: list[float] = field(default_factory=list)
	rsw: list[float] = field(default_factory=list)

@dataclass(slots=True)
class CellRockProperties:
	kro: list[float] = field(default_factory=list)
	krw: list[float] = field(default_factory=list)
	krg: list[float] = field(default_factory=list)
	pcow: list[float] = field(default_factory=list)
	pcgw: list[float] = field(default_factory=list)

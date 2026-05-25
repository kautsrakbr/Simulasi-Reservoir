from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(slots=True)
class GridSpec:
	nx: int = 1
	ny: int = 1
	nz: int = 1
	dx: float = 1.0
	dy: float = 1.0
	dz: float = 1.0

@dataclass(slots=True)
class CellData:
	cell_id: int
	i: int
	j: int
	k: int
	depth: float = 0.0
	porosity: float = 0.0
	perm_x: float = 0.0
	perm_y: float = 0.0
	perm_z: float = 0.0
	bulk_volume: float = 0.0
	pore_volume_multiplier: float = 1.0
	transmissibility_multiplier: float = 1.0
	is_active: bool = True

@dataclass(slots=True)
class Connection:
	from_cell_id: int
	to_cell_id: int
	direction: str
	area: float = 0.0
	distance: float = 0.0
	transmissibility: float = 0.0
	trans_multiplier: float = 1.0

@dataclass(slots=True)
class GridModel:
	spec: GridSpec = field(default_factory=GridSpec)
	cells: list[CellData] = field(default_factory=list)
	connections: list[Connection] = field(default_factory=list)

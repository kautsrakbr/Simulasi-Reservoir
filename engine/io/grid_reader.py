from __future__ import annotations

from engine.domain.grid import GridSpec


def read_grid_spec(source: dict[str, float | int]) -> GridSpec:
	return GridSpec(
		nx=int(source.get("nx", 1)),
		ny=int(source.get("ny", 1)),
		nz=int(source.get("nz", 1)),
		dx=float(source.get("dx", 1.0)),
		dy=float(source.get("dy", 1.0)),
		dz=float(source.get("dz", 1.0)),
		connectivity=int(source.get("connectivity", 5)),
	)

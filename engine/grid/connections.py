from __future__ import annotations

from engine.domain.grid import Connection, GridModel, GridSpec


def build_connections(grid_model: GridModel) -> list[Connection]:
	connections: list[Connection] = []
	spec = grid_model.spec
	for cell in grid_model.cells:
		for neighbor_id, direction in find_cartesian_neighbors(cell.cell_id, spec):
			if neighbor_id <= cell.cell_id:
				continue
			area, distance = get_connection_geometry(direction, spec)
			connections.append(
				Connection(
					from_cell_id=cell.cell_id,
					to_cell_id=neighbor_id,
					direction=direction,
					area=area,
					distance=distance,
				)
			)
	return connections


def find_cartesian_neighbors(cell_index: int, grid_spec: GridSpec) -> list[tuple[int, str]]:
	nx = grid_spec.nx
	ny = grid_spec.ny
	nz = grid_spec.nz
	plane_size = nx * ny
	k = cell_index // plane_size
	rem = cell_index % plane_size
	j = rem // nx
	i = rem % nx

	neighbors: list[tuple[int, str]] = []
	if i + 1 < nx:
		neighbors.append((cell_index + 1, "x+"))
	if j + 1 < ny:
		neighbors.append((cell_index + nx, "y+"))
	if k + 1 < nz:
		neighbors.append((cell_index + plane_size, "z+"))
	return neighbors


def get_connection_geometry(direction: str, grid_spec: GridSpec) -> tuple[float, float]:
	if direction == "x+":
		return grid_spec.dy * grid_spec.dz, grid_spec.dx
	if direction == "y+":
		return grid_spec.dx * grid_spec.dz, grid_spec.dy
	if direction == "z+":
		return grid_spec.dx * grid_spec.dy, grid_spec.dz
	return 0.0, 1.0

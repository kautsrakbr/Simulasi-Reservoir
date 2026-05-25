from __future__ import annotations

from engine.domain.grid import CellData, Connection, GridModel
from engine.common.constants import TRANSMISSIBILITY_UNIT_FACTOR


def compute_harmonic_permeability(k1: float, k2: float) -> float:
	if k1 <= 0.0 or k2 <= 0.0:
		return 0.0
	return 2.0 * k1 * k2 / (k1 + k2)


def compute_transmissibility(
	k1: float,
	k2: float,
	area: float,
	distance: float,
	unit_factor: float = TRANSMISSIBILITY_UNIT_FACTOR,
) -> float:
	if distance <= 0.0:
		return 0.0
	return unit_factor * compute_harmonic_permeability(k1, k2) * area / distance


def update_grid_transmissibility(grid_model: GridModel) -> GridModel:
	cell_lookup = {cell.cell_id: cell for cell in grid_model.cells}
	for connection in grid_model.connections:
		from_cell = cell_lookup[connection.from_cell_id]
		to_cell = cell_lookup[connection.to_cell_id]
		connection.transmissibility = compute_connection_transmissibility(connection, from_cell, to_cell)
	return grid_model


def compute_connection_transmissibility(connection: Connection, from_cell: CellData, to_cell: CellData) -> float:
	from_perm = _directional_permeability(from_cell, connection.direction)
	to_perm = _directional_permeability(to_cell, connection.direction)
	value = compute_transmissibility(
		k1=from_perm,
		k2=to_perm,
		area=connection.area,
		distance=connection.distance,
	)
	return value * connection.trans_multiplier


def _directional_permeability(cell: CellData, direction: str) -> float:
	if direction.startswith("x"):
		return cell.perm_x if cell.perm_x > 0.0 else 1.0
	if direction.startswith("y"):
		return cell.perm_y if cell.perm_y > 0.0 else 1.0
	if direction.startswith("z"):
		return cell.perm_z if cell.perm_z > 0.0 else 1.0
	return 1.0

from __future__ import annotations

from engine.domain.grid import CellData, GridModel, GridSpec
from engine.domain.project import ProjectConfig
from engine.grid.connections import build_connections
from engine.grid.geometry import compute_bulk_volume


def build_grid(project_config: ProjectConfig) -> GridModel:
	grid_model = GridModel(spec=project_config.grid_spec)
	grid_model.cells = build_cell_data(
		project_config.grid_spec,
		reference_depth=project_config.reference_data.reference_depth,
	)
	return attach_connections(grid_model)


def build_cell_data(grid_spec: GridSpec, reference_depth: float = 0.0) -> list[CellData]:
	cells: list[CellData] = []
	cell_id = 0
	bulk_volume = compute_bulk_volume(grid_spec.dx, grid_spec.dy, grid_spec.dz)
	for k in range(grid_spec.nz):
		for j in range(grid_spec.ny):
			for i in range(grid_spec.nx):
				cells.append(
					CellData(
						cell_id=cell_id,
						i=i,
						j=j,
						k=k,
						depth=reference_depth + (k + 0.5) * grid_spec.dz,
						porosity=0.2,
						perm_x=100.0,
						perm_y=100.0,
						perm_z=100.0,
						bulk_volume=bulk_volume,
					)
				)
				cell_id += 1
	return cells


def attach_connections(grid_model: GridModel) -> GridModel:
	grid_model.connections = build_connections(grid_model)
	return grid_model

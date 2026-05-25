from __future__ import annotations

from engine.domain.grid import GridModel
from engine.domain.project import ProjectConfig, ReferenceData
from engine.domain.state import ReservoirState


def initialize_state(project_config: ProjectConfig, grid_model: GridModel) -> ReservoirState:
	pressure = initialize_hydrostatic_pressure(project_config.reference_data, grid_model)
	sw, sg = initialize_saturations(project_config, grid_model)
	return ReservoirState(pressure=pressure, sw=sw, sg=sg)


def initialize_hydrostatic_pressure(reference_data: ReferenceData, grid_model: GridModel) -> list[float]:
	reference_depth = reference_data.reference_depth
	density = reference_data.water_density_reference if reference_data.water_density_reference > 0.0 else 1.0
	gradient = 0.433 * density
	return [
		reference_data.reference_pressure + gradient * (cell.depth - reference_depth)
		for cell in grid_model.cells
	]


def initialize_saturations(project_config: ProjectConfig, grid_model: GridModel) -> tuple[list[float], list[float]]:
	return (
		[project_config.initial_conditions.initial_sw for _ in grid_model.cells],
		[project_config.initial_conditions.initial_sg for _ in grid_model.cells],
	)

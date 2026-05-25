from __future__ import annotations

from engine.domain.grid import GridModel
from engine.domain.project import ProjectConfig, ReferenceData
from engine.domain.state import ReservoirState


def initialize_state(project_config: ProjectConfig, grid_model: GridModel) -> ReservoirState:
	pressure = initialize_hydrostatic_pressure(project_config.reference_data, grid_model)
	sw, sg = initialize_saturations(project_config, grid_model)
	return ReservoirState(pressure=pressure, sw=sw, sg=sg)


def initialize_hydrostatic_pressure(reference_data: ReferenceData, grid_model: GridModel) -> list[float]:
	return [reference_data.reference_pressure for _ in grid_model.cells]


def initialize_saturations(project_config: ProjectConfig, grid_model: GridModel) -> tuple[list[float], list[float]]:
	del project_config
	return [0.0 for _ in grid_model.cells], [0.0 for _ in grid_model.cells]

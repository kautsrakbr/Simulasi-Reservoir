from __future__ import annotations

from engine.domain.project import ProjectConfig
from engine.io.grid_reader import read_grid_spec
from engine.io.ref_reader import read_reference_data


def load_project(payload: dict[str, object]) -> ProjectConfig:
	project = ProjectConfig()
	project.name = str(payload.get("name", project.name))
	project.description = str(payload.get("description", project.description))
	project.reference_data = read_reference_data(dict(payload.get("reference_data", {})))
	project.grid_spec = read_grid_spec(dict(payload.get("grid_spec", {})))
	return project

from __future__ import annotations

from engine.domain.project import ProjectConfig


def write_project(project_config: ProjectConfig) -> dict[str, object]:
	return {
		"name": project_config.name,
		"description": project_config.description,
		"reference_data": {
			"reference_depth": project_config.reference_data.reference_depth,
			"reference_pressure": project_config.reference_data.reference_pressure,
		},
		"grid_spec": {
			"nx": project_config.grid_spec.nx,
			"ny": project_config.grid_spec.ny,
			"nz": project_config.grid_spec.nz,
			"dx": project_config.grid_spec.dx,
			"dy": project_config.grid_spec.dy,
			"dz": project_config.grid_spec.dz,
		},
	}

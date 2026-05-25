from __future__ import annotations

from engine.domain.project import ProjectConfig


def create_empty_project(name: str = "Simulasi Reservoir") -> ProjectConfig:
	return ProjectConfig(name=name)


def update_project_metadata(
	project_config: ProjectConfig,
	*,
	name: str | None = None,
	description: str | None = None,
) -> ProjectConfig:
	if name is not None:
		project_config.name = name
	if description is not None:
		project_config.description = description
	return project_config

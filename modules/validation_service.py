from __future__ import annotations

from engine.domain.project import ProjectConfig


def validate_project(project_config: ProjectConfig) -> list[str]:
	errors: list[str] = []
	errors.extend(validate_grid_inputs(project_config))
	errors.extend(validate_pvt_inputs(project_config))
	errors.extend(validate_rock_inputs(project_config))
	errors.extend(validate_initial_state(project_config))
	return errors


def validate_grid_inputs(project_config: ProjectConfig) -> list[str]:
	errors: list[str] = []
	if project_config.grid_spec.nx <= 0:
		errors.append("Grid nx harus lebih besar dari 0.")
	if project_config.grid_spec.ny <= 0:
		errors.append("Grid ny harus lebih besar dari 0.")
	if project_config.grid_spec.nz <= 0:
		errors.append("Grid nz harus lebih besar dari 0.")
	return errors


def validate_pvt_inputs(project_config: ProjectConfig) -> list[str]:
	if project_config.pvt_tables:
		return []
	return ["Data PVT belum diisi."]


def validate_rock_inputs(project_config: ProjectConfig) -> list[str]:
	if project_config.rock_tables:
		return []
	return ["Data rock-fluid belum diisi."]


def validate_initial_state(project_config: ProjectConfig) -> list[str]:
	if project_config.reference_data.reference_pressure > 0.0:
		return []
	return ["Reference pressure harus lebih besar dari 0."]

from __future__ import annotations

from pathlib import Path

from engine.domain.project import ProjectConfig
from engine.io.project_loader import load_project_json as io_load_project_json
from engine.io.project_writer import write_project_json


def create_empty_project(name: str = "CoreReservoir") -> ProjectConfig:
	project = ProjectConfig(name=name)
	project.description = "Desktop reservoir simulation workspace."
	project.reference_data.reference_depth = 6500.0
	project.reference_data.reference_pressure = 2500.0
	project.reference_data.water_density_reference = 1.0
	project.grid_spec.nx = 2
	project.grid_spec.ny = 1
	project.grid_spec.nz = 2
	project.grid_spec.dx = 100.0
	project.grid_spec.dy = 100.0
	project.grid_spec.dz = 50.0
	project.initial_conditions.reference_depth = 6500.0
	project.initial_conditions.initial_sw = 0.25
	project.initial_conditions.initial_sg = 0.05
	project.solver.initial_timestep_days = 1.0
	project.solver.min_timestep_days = 0.05
	project.solver.max_time_days = 3.0
	project.solver.timestep_growth_factor = 1.1
	project.solver.timestep_shrink_factor = 0.5
	project.solver.max_step_retries = 8
	project.solver.max_newton_iterations = 10
	project.solver.residual_tolerance = 1e-4
	project.solver.parameter_tolerance = 1e-6
	project.solver.residual_norm_floor = 0.1
	project.solver.newton_pressure_damping = 0.7
	project.solver.newton_saturation_damping = 0.7
	project.solver.max_pressure_correction = 10.0
	project.solver.max_saturation_correction = 0.001
	project.run.case_name = f"{name} Base Case"
	load_example_pvt_tables(project)
	load_example_rock_tables(project)
	mark_project_clean(project)
	return project


def update_project_metadata(
	project_config: ProjectConfig,
	*,
	name: str | None = None,
	description: str | None = None,
	case_name: str | None = None,
	reference_pressure: float | None = None,
) -> ProjectConfig:
	if name is not None:
		project_config.name = name
	if description is not None:
		project_config.description = description
	if case_name is not None:
		project_config.run.case_name = case_name
	if reference_pressure is not None:
		project_config.reference_data.reference_pressure = reference_pressure
	project_config.is_dirty = True
	return project_config


def update_grid_spec(
	project_config: ProjectConfig,
	*,
	nx: int,
	ny: int,
	nz: int,
	dx: float,
	dy: float,
	dz: float,
) -> ProjectConfig:
	project_config.grid_spec.nx = nx
	project_config.grid_spec.ny = ny
	project_config.grid_spec.nz = nz
	project_config.grid_spec.dx = dx
	project_config.grid_spec.dy = dy
	project_config.grid_spec.dz = dz
	project_config.is_dirty = True
	return project_config


def update_initial_conditions(
	project_config: ProjectConfig,
	*,
	reference_depth: float,
	initial_sw: float,
	initial_sg: float,
) -> ProjectConfig:
	project_config.initial_conditions.reference_depth = reference_depth
	project_config.initial_conditions.initial_sw = initial_sw
	project_config.initial_conditions.initial_sg = initial_sg
	project_config.reference_data.reference_depth = reference_depth
	project_config.is_dirty = True
	return project_config


def update_solver_config(
	project_config: ProjectConfig,
	*,
	initial_timestep_days: float | None = None,
	min_timestep_days: float | None = None,
	max_time_days: float | None = None,
	timestep_growth_factor: float | None = None,
	timestep_shrink_factor: float | None = None,
	max_step_retries: int | None = None,
	max_newton_iterations: int | None = None,
	residual_tolerance: float | None = None,
	parameter_tolerance: float | None = None,
	residual_norm_floor: float | None = None,
	newton_pressure_damping: float | None = None,
	newton_saturation_damping: float | None = None,
	max_pressure_correction: float | None = None,
	max_saturation_correction: float | None = None,
) -> ProjectConfig:
	if initial_timestep_days is not None:
		project_config.solver.initial_timestep_days = initial_timestep_days
	if min_timestep_days is not None:
		project_config.solver.min_timestep_days = min_timestep_days
	if max_time_days is not None:
		project_config.solver.max_time_days = max_time_days
	if timestep_growth_factor is not None:
		project_config.solver.timestep_growth_factor = timestep_growth_factor
	if timestep_shrink_factor is not None:
		project_config.solver.timestep_shrink_factor = timestep_shrink_factor
	if max_step_retries is not None:
		project_config.solver.max_step_retries = max_step_retries
	if max_newton_iterations is not None:
		project_config.solver.max_newton_iterations = max_newton_iterations
	if residual_tolerance is not None:
		project_config.solver.residual_tolerance = residual_tolerance
	if parameter_tolerance is not None:
		project_config.solver.parameter_tolerance = parameter_tolerance
	if residual_norm_floor is not None:
		project_config.solver.residual_norm_floor = residual_norm_floor
	if newton_pressure_damping is not None:
		project_config.solver.newton_pressure_damping = newton_pressure_damping
	if newton_saturation_damping is not None:
		project_config.solver.newton_saturation_damping = newton_saturation_damping
	if max_pressure_correction is not None:
		project_config.solver.max_pressure_correction = max_pressure_correction
	if max_saturation_correction is not None:
		project_config.solver.max_saturation_correction = max_saturation_correction
	project_config.is_dirty = True
	return project_config


def load_example_pvt_tables(project_config: ProjectConfig) -> ProjectConfig:
	project_config.pvt_tables = {
		"bo": [(1000.0, 1.22), (2500.0, 1.08), (4000.0, 0.98)],
		"bw": [(1000.0, 1.03), (2500.0, 1.01), (4000.0, 0.99)],
		"bg": [(1000.0, 0.005), (2500.0, 0.003), (4000.0, 0.002)],
		"mu_o": [(1000.0, 2.1), (2500.0, 1.8), (4000.0, 1.5)],
		"mu_w": [(1000.0, 0.55), (2500.0, 0.58), (4000.0, 0.62)],
		"mu_g": [(1000.0, 0.02), (2500.0, 0.025), (4000.0, 0.03)],
		"rso": [(1000.0, 180.0), (2500.0, 320.0), (4000.0, 420.0)],
		"rsw": [(1000.0, 2.0), (2500.0, 2.5), (4000.0, 3.0)],
	}
	project_config.is_dirty = True
	return project_config


def clear_pvt_tables(project_config: ProjectConfig) -> ProjectConfig:
	project_config.pvt_tables.clear()
	project_config.is_dirty = True
	return project_config


def load_example_rock_tables(project_config: ProjectConfig) -> ProjectConfig:
	project_config.rock_tables = {
		"kro": [(0.0, 1.0), (0.3, 0.75), (1.0, 0.0)],
		"krw": [(0.0, 0.0), (0.3, 0.05), (1.0, 1.0)],
		"krg": [(0.0, 0.0), (0.2, 0.04), (1.0, 1.0)],
		"pcow": [(0.0, 12.0), (0.3, 7.0), (1.0, 0.0)],
		"pcgw": [(0.0, 9.0), (0.2, 5.0), (1.0, 0.0)],
	}
	project_config.is_dirty = True
	return project_config


def clear_rock_tables(project_config: ProjectConfig) -> ProjectConfig:
	project_config.rock_tables.clear()
	project_config.is_dirty = True
	return project_config


def mark_project_clean(project_config: ProjectConfig) -> ProjectConfig:
	project_config.is_dirty = False
	return project_config


def save_project_json(project_config: ProjectConfig, file_path: str | Path) -> Path:
	target = write_project_json(project_config, file_path)
	mark_project_clean(project_config)
	return target


def load_project_json(file_path: str | Path) -> ProjectConfig:
	project = io_load_project_json(file_path)
	mark_project_clean(project)
	return project

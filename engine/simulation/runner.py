from __future__ import annotations

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult
from engine.grid.builder import build_grid
from engine.reporting.result_builder import build_run_result
from engine.simulation.initializer import initialize_state


def run_simulation(project_config: ProjectConfig) -> RunResult:
	grid_model = build_grid(project_config)
	initialize_state(project_config, grid_model)
	return build_run_result(case_name=project_config.run.case_name)


def run_timestep(*args: object, **kwargs: object) -> object:
	del args, kwargs
	raise NotImplementedError("Run timestep belum diimplementasikan.")


def commit_timestep_state(state: object) -> object:
	return state


def emit_progress(message: str) -> str:
	return message

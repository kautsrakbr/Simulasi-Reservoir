from __future__ import annotations

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult
from engine.simulation.runner import IterationCallback, run_simulation as run_engine_simulation
from modules.validation_service import validate_project


def run_simulation(project_config: ProjectConfig, on_iteration: IterationCallback | None = None) -> RunResult:
	errors = validate_project(project_config)
	if errors:
		raise ValueError(" ".join(errors))

	return run_engine_simulation(project_config, on_iteration=on_iteration)


def validate_and_run(project_config: ProjectConfig, on_iteration: IterationCallback | None = None) -> RunResult:
	return run_simulation(project_config, on_iteration=on_iteration)


def load_results(run_result: RunResult) -> RunResult:
	return run_result

from __future__ import annotations

from collections.abc import Callable

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult
from engine.simulation.runner import run_simulation as run_engine_simulation
from modules.validation_service import validate_project


def run_simulation(
	project_config: ProjectConfig,
	*,
	progress_callback: Callable[[str], None] | None = None,
	should_cancel: Callable[[], bool] | None = None,
) -> RunResult:
	errors = validate_project(project_config)
	if errors:
		raise ValueError(" ".join(errors))

	return run_engine_simulation(
		project_config,
		progress_callback=progress_callback,
		should_cancel=should_cancel,
	)


def validate_and_run(
	project_config: ProjectConfig,
	*,
	progress_callback: Callable[[str], None] | None = None,
	should_cancel: Callable[[], bool] | None = None,
) -> RunResult:
	return run_simulation(
		project_config,
		progress_callback=progress_callback,
		should_cancel=should_cancel,
	)


def load_results(run_result: RunResult) -> RunResult:
	return run_result

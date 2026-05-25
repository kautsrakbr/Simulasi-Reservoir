from __future__ import annotations

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult
from engine.reporting.result_builder import build_run_result
from modules.validation_service import validate_project


def run_simulation(project_config: ProjectConfig) -> RunResult:
	errors = validate_project(project_config)
	if errors:
		raise ValueError(" ".join(errors))

	return build_run_result(case_name=project_config.run.case_name)


def validate_and_run(project_config: ProjectConfig) -> RunResult:
	return run_simulation(project_config)


def load_results(run_result: RunResult) -> RunResult:
	return run_result

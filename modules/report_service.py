from __future__ import annotations

from pathlib import Path

from engine.domain.results import RunResult
from engine.reporting.exporters import export_run_summary_text


def export_summary(run_result: RunResult, output_path: str | Path) -> Path:
	return export_run_summary_text(run_result, output_path)

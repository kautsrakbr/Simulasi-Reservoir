from __future__ import annotations

from pathlib import Path

from engine.domain.results import RunResult
from engine.reporting.summary import build_run_summary


def export_run_summary_text(run_result: RunResult, output_path: str | Path) -> Path:
	target = Path(output_path)
	summary = build_run_summary(run_result)
	lines = [f"{key}: {value}" for key, value in summary.items()]
	target.write_text("\n".join(lines), encoding="utf-8")
	return target

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult
from modules.simulation_service import validate_and_run


class RunWorker(QObject):
	started = Signal()
	progress = Signal(str)
	warning = Signal(str)
	finished = Signal(object)
	failed = Signal(str)

	def __init__(self, project_config: ProjectConfig) -> None:
		super().__init__()
		self.project_config = project_config

	@Slot()
	def run(self) -> None:
		self.started.emit()
		self.progress.emit("Memulai validasi model.")

		def _on_iteration(time_days: float, iteration: int, residual_norm: float, converged: bool) -> None:
			status = "konvergen" if converged else "lanjut"
			self.progress.emit(
				f"  t={time_days:.2f}d  ·  iterasi {iteration}  ·  residual_norm={residual_norm:.3e}  ·  {status}"
			)

		try:
			run_result = validate_and_run(self.project_config, on_iteration=_on_iteration)
		except Exception as exc:
			self.failed.emit(str(exc))
			return

		self.finished.emit(run_result)

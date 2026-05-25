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
		try:
			run_result = validate_and_run(self.project_config)
		except Exception as exc:
			self.failed.emit(str(exc))
			return

		self.progress.emit("Run placeholder selesai.")
		self.finished.emit(run_result)

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
		self._cancel_requested = False

	@Slot()
	def request_cancel(self) -> None:
		self._cancel_requested = True
		self.progress.emit("Permintaan cancel diterima, menghentikan run secara aman...")

	def is_cancel_requested(self) -> bool:
		return self._cancel_requested

	@Slot()
	def run(self) -> None:
		self.started.emit()
		self.progress.emit("Memulai validasi model.")
		try:
			run_result = validate_and_run(
				self.project_config,
				progress_callback=self.progress.emit,
				should_cancel=self.is_cancel_requested,
			)
		except Exception as exc:
			self.failed.emit(str(exc))
			return

		for message in run_result.warnings:
			self.warning.emit(message)
		self.progress.emit("Run selesai, menyusun payload hasil.")
		self.finished.emit(run_result)

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from engine.domain.project import ProjectConfig


class RunPage(QWidget):
	runRequested = Signal()

	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Run Page")
		self.project_label = QLabel()
		self.grid_label = QLabel()
		self.dirty_label = QLabel()
		self.status_label = QLabel()
		self.validation_label = QLabel()
		self.validation_label.setWordWrap(True)
		self.run_button = QPushButton("Run Placeholder Simulation", self)

		layout.addWidget(title)
		layout.addWidget(self.project_label)
		layout.addWidget(self.grid_label)
		layout.addWidget(self.dirty_label)
		layout.addWidget(self.status_label)
		layout.addWidget(self.validation_label)
		layout.addWidget(self.run_button)

		self.run_button.clicked.connect(self.runRequested)

	def set_project_state(self, project_config: ProjectConfig, validation_errors: list[str]) -> None:
		self.project_label.setText(f"Case aktif: {project_config.run.case_name}")
		cell_count = project_config.grid_spec.nx * project_config.grid_spec.ny * project_config.grid_spec.nz
		self.grid_label.setText(
			f"Grid aktif: {project_config.grid_spec.nx} x {project_config.grid_spec.ny} x {project_config.grid_spec.nz} ({cell_count} cells)"
		)
		if project_config.is_dirty:
			self.dirty_label.setText("Perubahan model terdeteksi: run ulang disarankan.")
		else:
			self.dirty_label.setText("Model sinkron dengan hasil run terakhir.")
		if validation_errors:
			self.status_label.setText("Run status: blocked")
			self.validation_label.setText("Masalah validasi: " + " | ".join(validation_errors))
			self.run_button.setEnabled(False)
		else:
			self.status_label.setText("Run status: ready")
			self.validation_label.setText("Model siap untuk run placeholder.")
			self.run_button.setEnabled(True)

	def set_run_feedback(self, message: str) -> None:
		self.status_label.setText(message)

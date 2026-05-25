from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from engine.domain.project import ProjectConfig


class DashboardPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Dashboard")
		description = QLabel(
			"Halaman ini akan menampilkan readiness model, status validasi, dan ringkasan run."
		)
		description.setWordWrap(True)
		self.project_label = QLabel()
		self.case_label = QLabel()
		self.grid_label = QLabel()
		self.initial_label = QLabel()
		self.dirty_label = QLabel()
		self.readiness_label = QLabel()
		self.validation_label = QLabel()
		self.validation_label.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)
		layout.addWidget(self.project_label)
		layout.addWidget(self.case_label)
		layout.addWidget(self.grid_label)
		layout.addWidget(self.initial_label)
		layout.addWidget(self.dirty_label)
		layout.addWidget(self.readiness_label)
		layout.addWidget(self.validation_label)

	def set_project_overview(self, project_config: ProjectConfig, validation_errors: list[str]) -> None:
		self.project_label.setText(f"Project: {project_config.name}")
		self.case_label.setText(f"Case: {project_config.run.case_name}")
		cell_count = project_config.grid_spec.nx * project_config.grid_spec.ny * project_config.grid_spec.nz
		self.grid_label.setText(
			f"Grid: {project_config.grid_spec.nx} x {project_config.grid_spec.ny} x {project_config.grid_spec.nz} ({cell_count} cells)"
		)
		self.initial_label.setText(
			"Initial: "
			f"depth={project_config.initial_conditions.reference_depth:.2f} ft, "
			f"Sw={project_config.initial_conditions.initial_sw:.4f}, "
			f"Sg={project_config.initial_conditions.initial_sg:.4f}"
		)
		if project_config.is_dirty:
			self.dirty_label.setText("Project state: Dirty (belum disimpan / belum dirun ulang)")
		else:
			self.dirty_label.setText("Project state: Clean")
		if validation_errors:
			self.readiness_label.setText("Status: Incomplete")
			self.validation_label.setText("Validation: " + " | ".join(validation_errors))
		else:
			self.readiness_label.setText("Status: Ready")
			self.validation_label.setText("Validation: Semua input minimum sudah lolos.")

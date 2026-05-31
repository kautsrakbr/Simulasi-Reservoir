from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
	QDoubleSpinBox,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QScrollArea,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


class GridPage(QWidget):
	gridChanged = Signal(int, int, int, float, float, float)

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setContentsMargins(24, 20, 24, 20)
		outer.setSpacing(12)

		# ── Header ──
		hdr = QHBoxLayout()
		title = QLabel("Grid")
		title.setObjectName("pageTitle")
		self._stats_label = QLabel()
		self._stats_label.setObjectName("metaLabel")
		hdr.addWidget(title)
		hdr.addStretch()
		hdr.addWidget(self._stats_label)
		outer.addLayout(hdr)

		# ── Scroll area ──
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QScrollArea.Shape.NoFrame)
		container = QWidget()
		container_layout = QVBoxLayout(container)
		container_layout.setContentsMargins(0, 0, 0, 0)
		container_layout.setSpacing(14)

		# Grid Dimensions group
		dim_grp = QGroupBox("Grid Dimensions")
		dim_form = QFormLayout(dim_grp)
		dim_form.setSpacing(8)
		self.nx_input = QSpinBox()
		self.ny_input = QSpinBox()
		self.nz_input = QSpinBox()
		for sp in (self.nx_input, self.ny_input, self.nz_input):
			sp.setMinimum(1)
			sp.setMaximum(1_000)
		dim_form.addRow("NX  (cells, X direction)", self.nx_input)
		dim_form.addRow("NY  (cells, Y direction)", self.ny_input)
		dim_form.addRow("NZ  (cells, Z direction)", self.nz_input)
		container_layout.addWidget(dim_grp)

		# Cell Size group
		size_grp = QGroupBox("Cell Size")
		size_form = QFormLayout(size_grp)
		size_form.setSpacing(8)
		self.dx_input = QDoubleSpinBox()
		self.dy_input = QDoubleSpinBox()
		self.dz_input = QDoubleSpinBox()
		for sp in (self.dx_input, self.dy_input, self.dz_input):
			sp.setMinimum(0.01)
			sp.setMaximum(1_000_000.0)
			sp.setDecimals(3)
			sp.setValue(1.0)
			sp.setSuffix(" ft")
		size_form.addRow("DX  (cell length, X)", self.dx_input)
		size_form.addRow("DY  (cell length, Y)", self.dy_input)
		size_form.addRow("DZ  (cell thickness, Z)", self.dz_input)
		container_layout.addWidget(size_grp)
		container_layout.addStretch(1)

		scroll.setWidget(container)
		outer.addWidget(scroll, 1)

		for sp in (self.nx_input, self.ny_input, self.nz_input,
				   self.dx_input, self.dy_input, self.dz_input):
			sp.valueChanged.connect(self._emit_change)

	def set_project(self, project_config: ProjectConfig) -> None:
		blockers = [
			QSignalBlocker(self.nx_input), QSignalBlocker(self.ny_input), QSignalBlocker(self.nz_input),
			QSignalBlocker(self.dx_input), QSignalBlocker(self.dy_input), QSignalBlocker(self.dz_input),
		]
		self.nx_input.setValue(project_config.grid_spec.nx)
		self.ny_input.setValue(project_config.grid_spec.ny)
		self.nz_input.setValue(project_config.grid_spec.nz)
		self.dx_input.setValue(project_config.grid_spec.dx)
		self.dy_input.setValue(project_config.grid_spec.dy)
		self.dz_input.setValue(project_config.grid_spec.dz)
		nx, ny, nz = project_config.grid_spec.nx, project_config.grid_spec.ny, project_config.grid_spec.nz
		cells = nx * ny * nz
		vol = cells * project_config.grid_spec.dx * project_config.grid_spec.dy * project_config.grid_spec.dz
		self._stats_label.setText(f"{nx}\u00d7{ny}\u00d7{nz} = {cells} cells  |  Volume \u2248 {vol:,.0f} ft\u00b3")
		del blockers

	def _emit_change(self) -> None:
		self.gridChanged.emit(
			self.nx_input.value(), self.ny_input.value(), self.nz_input.value(),
			self.dx_input.value(), self.dy_input.value(), self.dz_input.value(),
		)

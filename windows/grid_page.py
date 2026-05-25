from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QSpinBox, QWidget

from engine.domain.project import ProjectConfig


class GridPage(QWidget):
	gridChanged = Signal(int, int, int, float, float, float)

	def __init__(self) -> None:
		super().__init__()

		layout = QFormLayout(self)
		self.nx_input = QSpinBox(self)
		self.ny_input = QSpinBox(self)
		self.nz_input = QSpinBox(self)
		self.dx_input = QDoubleSpinBox(self)
		self.dy_input = QDoubleSpinBox(self)
		self.dz_input = QDoubleSpinBox(self)

		for spin_box in (self.nx_input, self.ny_input, self.nz_input):
			spin_box.setMinimum(1)
			spin_box.setMaximum(1_000)

		for spin_box in (self.dx_input, self.dy_input, self.dz_input):
			spin_box.setMinimum(0.01)
			spin_box.setMaximum(1_000_000.0)
			spin_box.setDecimals(3)
			spin_box.setValue(1.0)

		layout.addRow("NX", self.nx_input)
		layout.addRow("NY", self.ny_input)
		layout.addRow("NZ", self.nz_input)
		layout.addRow("DX", self.dx_input)
		layout.addRow("DY", self.dy_input)
		layout.addRow("DZ", self.dz_input)

		self.nx_input.valueChanged.connect(self._emit_change)
		self.ny_input.valueChanged.connect(self._emit_change)
		self.nz_input.valueChanged.connect(self._emit_change)
		self.dx_input.valueChanged.connect(self._emit_change)
		self.dy_input.valueChanged.connect(self._emit_change)
		self.dz_input.valueChanged.connect(self._emit_change)

	def set_project(self, project_config: ProjectConfig) -> None:
		blockers = [
			QSignalBlocker(self.nx_input),
			QSignalBlocker(self.ny_input),
			QSignalBlocker(self.nz_input),
			QSignalBlocker(self.dx_input),
			QSignalBlocker(self.dy_input),
			QSignalBlocker(self.dz_input),
		]
		self.nx_input.setValue(project_config.grid_spec.nx)
		self.ny_input.setValue(project_config.grid_spec.ny)
		self.nz_input.setValue(project_config.grid_spec.nz)
		self.dx_input.setValue(project_config.grid_spec.dx)
		self.dy_input.setValue(project_config.grid_spec.dy)
		self.dz_input.setValue(project_config.grid_spec.dz)
		del blockers

	def _emit_change(self) -> None:
		self.gridChanged.emit(
			self.nx_input.value(),
			self.ny_input.value(),
			self.nz_input.value(),
			self.dx_input.value(),
			self.dy_input.value(),
			self.dz_input.value(),
		)

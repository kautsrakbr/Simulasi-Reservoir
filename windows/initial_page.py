from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QWidget

from engine.domain.project import ProjectConfig


class InitialPage(QWidget):
	initialConditionsChanged = Signal(float, float, float)

	def __init__(self) -> None:
		super().__init__()

		layout = QFormLayout(self)
		title = QLabel("Initial Conditions")
		self.reference_depth_input = QDoubleSpinBox(self)
		self.reference_depth_input.setRange(0.0, 100_000.0)
		self.reference_depth_input.setDecimals(2)
		self.initial_sw_input = QDoubleSpinBox(self)
		self.initial_sw_input.setRange(0.0, 1.0)
		self.initial_sw_input.setDecimals(4)
		self.initial_sg_input = QDoubleSpinBox(self)
		self.initial_sg_input.setRange(0.0, 1.0)
		self.initial_sg_input.setDecimals(4)
		self.initial_so_label = QLabel()
		self.description = QLabel()
		self.description.setWordWrap(True)

		layout.addRow(title)
		layout.addRow("Reference Depth", self.reference_depth_input)
		layout.addRow("Initial Sw", self.initial_sw_input)
		layout.addRow("Initial Sg", self.initial_sg_input)
		layout.addRow("Computed So", self.initial_so_label)
		layout.addRow(self.description)

		self.reference_depth_input.valueChanged.connect(self._emit_change)
		self.initial_sw_input.valueChanged.connect(self._emit_change)
		self.initial_sg_input.valueChanged.connect(self._emit_change)

	def set_project(self, project_config: ProjectConfig) -> None:
		blockers = [
			QSignalBlocker(self.reference_depth_input),
			QSignalBlocker(self.initial_sw_input),
			QSignalBlocker(self.initial_sg_input),
		]
		self.reference_depth_input.setValue(project_config.initial_conditions.reference_depth)
		self.initial_sw_input.setValue(project_config.initial_conditions.initial_sw)
		self.initial_sg_input.setValue(project_config.initial_conditions.initial_sg)
		self._update_so_label(project_config.initial_conditions.initial_sw, project_config.initial_conditions.initial_sg)
		del blockers
		self.description.setText(
			"Reference pressure saat ini: "
			f"{project_config.reference_data.reference_pressure:.2f} psi. "
			"Saturasi awal sekarang sudah dipakai oleh placeholder runner."
		)

	def _emit_change(self) -> None:
		sw = self.initial_sw_input.value()
		sg = self.initial_sg_input.value()
		self._update_so_label(sw, sg)
		self.initialConditionsChanged.emit(self.reference_depth_input.value(), sw, sg)

	def _update_so_label(self, sw: float, sg: float) -> None:
		so = max(0.0, 1.0 - sw - sg)
		self.initial_so_label.setText(f"{so:.4f}")

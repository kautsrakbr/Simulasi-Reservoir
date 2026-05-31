from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
	QDoubleSpinBox,
	QFormLayout,
	QFrame,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QScrollArea,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


class InitialPage(QWidget):
	initialConditionsChanged = Signal(float, float, float)

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setContentsMargins(24, 20, 24, 20)
		outer.setSpacing(12)

		# ── Header ──
		title = QLabel("Initial Conditions")
		title.setObjectName("pageTitle")
		outer.addWidget(title)

		# ── Scroll area ──
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QScrollArea.Shape.NoFrame)
		container = QWidget()
		c_layout = QVBoxLayout(container)
		c_layout.setContentsMargins(0, 0, 0, 0)
		c_layout.setSpacing(14)

		# Reference point group
		ref_grp = QGroupBox("Reference Point")
		ref_form = QFormLayout(ref_grp)
		ref_form.setSpacing(8)
		self.reference_depth_input = QDoubleSpinBox()
		self.reference_depth_input.setRange(0.0, 100_000.0)
		self.reference_depth_input.setDecimals(2)
		self.reference_depth_input.setSuffix(" ft")
		ref_form.addRow("Reference Depth", self.reference_depth_input)
		c_layout.addWidget(ref_grp)

		# Initial saturations group
		sat_grp = QGroupBox("Initial Saturations")
		sat_form = QFormLayout(sat_grp)
		sat_form.setSpacing(8)
		self.initial_sw_input = QDoubleSpinBox()
		self.initial_sw_input.setRange(0.0, 1.0)
		self.initial_sw_input.setDecimals(4)
		self.initial_sg_input = QDoubleSpinBox()
		self.initial_sg_input.setRange(0.0, 1.0)
		self.initial_sg_input.setDecimals(4)
		self.initial_so_label = QLabel()
		self.initial_so_label.setObjectName("metaValue")
		sat_form.addRow("Initial Sw  (water saturation)", self.initial_sw_input)
		sat_form.addRow("Initial Sg  (gas saturation)", self.initial_sg_input)
		sat_form.addRow("Computed So  (oil, 1\u2212Sw\u2212Sg)", self.initial_so_label)
		c_layout.addWidget(sat_grp)

		# Info card
		info_card = QFrame()
		info_card.setObjectName("card")
		info_box = QVBoxLayout(info_card)
		info_box.setContentsMargins(16, 12, 16, 12)
		self.description = QLabel()
		self.description.setObjectName("metaLabel")
		self.description.setWordWrap(True)
		info_box.addWidget(self.description)
		c_layout.addWidget(info_card)
		c_layout.addStretch(1)

		scroll.setWidget(container)
		outer.addWidget(scroll, 1)

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
		self._update_so_label(
			project_config.initial_conditions.initial_sw,
			project_config.initial_conditions.initial_sg,
		)
		del blockers
		self.description.setText(
			f"Reference pressure: {project_config.reference_data.reference_pressure:.2f} psi  "
			f"at depth {project_config.initial_conditions.reference_depth:.0f} ft.  "
			"Saturasi awal digunakan oleh simulator sebagai kondisi awal seluruh cells."
		)

	def _emit_change(self) -> None:
		sw = self.initial_sw_input.value()
		sg = self.initial_sg_input.value()
		self._update_so_label(sw, sg)
		self.initialConditionsChanged.emit(self.reference_depth_input.value(), sw, sg)

	def _update_so_label(self, sw: float, sg: float) -> None:
		so = max(0.0, 1.0 - sw - sg)
		self.initial_so_label.setText(f"{so:.4f}")

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
	QDoubleSpinBox,
	QFormLayout,
	QFrame,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


def _form(parent: QWidget | None = None) -> QFormLayout:
	f = QFormLayout(parent)
	f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
	f.setHorizontalSpacing(14)
	f.setVerticalSpacing(8)
	f.setContentsMargins(10, 10, 10, 10)
	return f


class InitialPage(QWidget):
	initialConditionsChanged = Signal(float, float, float)

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setSpacing(8)
		outer.setContentsMargins(14, 14, 14, 14)

		# ── Page header ───────────────────────────────────────────────
		hdr = QHBoxLayout()
		title = QLabel("Kondisi Awal")
		title.setObjectName("pageTitle")
		hdr.addWidget(title)
		hdr.addStretch()
		outer.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		outer.addWidget(sep)

		# ── Group: Reference & Initial Saturations ────────────────────
		grp = QGroupBox("Referensi & Saturasi Awal")
		frm = _form(grp)
		self.reference_depth_input = QDoubleSpinBox()
		self.reference_depth_input.setRange(0.0, 100_000.0)
		self.reference_depth_input.setDecimals(2)
		self.initial_sw_input = QDoubleSpinBox()
		self.initial_sw_input.setRange(0.0, 1.0)
		self.initial_sw_input.setDecimals(4)
		self.initial_sw_input.setSingleStep(0.01)
		self.initial_sg_input = QDoubleSpinBox()
		self.initial_sg_input.setRange(0.0, 1.0)
		self.initial_sg_input.setDecimals(4)
		self.initial_sg_input.setSingleStep(0.01)

		# So: styled read-only display
		self.initial_so_label = QLabel("1.0000")
		self.initial_so_label.setObjectName("soDisplayChip")
		self.initial_so_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.initial_so_label.setFixedWidth(90)

		frm.addRow("Kedalaman Referensi (ft)", self.reference_depth_input)
		frm.addRow("Saturasi Air Awal  Sw", self.initial_sw_input)
		frm.addRow("Saturasi Gas Awal  Sg", self.initial_sg_input)
		frm.addRow("Saturasi Minyak  So  =", self.initial_so_label)
		outer.addWidget(grp)

		# ── Description info label ────────────────────────────────────
		self.description = QLabel()
		self.description.setWordWrap(True)
		self.description.setObjectName("pageHintLabel")
		outer.addWidget(self.description)

		outer.addStretch()

		# ── Wire signals ──────────────────────────────────────────────
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
			"Tekanan referensi saat ini: "
			f"{project_config.reference_data.reference_pressure:.2f} psi. "
			"Saturasi awal dipakai sebagai kondisi awal simulasi."
		)

	def _emit_change(self) -> None:
		sw = self.initial_sw_input.value()
		sg = self.initial_sg_input.value()
		self._update_so_label(sw, sg)
		self.initialConditionsChanged.emit(self.reference_depth_input.value(), sw, sg)

	def _update_so_label(self, sw: float, sg: float) -> None:
		so = max(0.0, 1.0 - sw - sg)
		self.initial_so_label.setText(f"{so:.4f}")
		is_valid = (sw + sg) <= 1.0
		self.initial_so_label.setProperty("soValid", is_valid)
		self.initial_so_label.style().unpolish(self.initial_so_label)
		self.initial_so_label.style().polish(self.initial_so_label)

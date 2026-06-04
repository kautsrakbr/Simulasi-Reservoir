from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
	QDoubleSpinBox,
	QFormLayout,
	QFrame,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QSpinBox,
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


class GridPage(QWidget):
	gridChanged = Signal(int, int, int, float, float, float)

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setSpacing(8)
		outer.setContentsMargins(14, 14, 14, 14)

		# ── Page header ───────────────────────────────────────────────
		hdr = QHBoxLayout()
		title = QLabel("Grid Reservoir")
		title.setObjectName("pageTitle")
		hdr.addWidget(title)
		hdr.addStretch()
		outer.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		outer.addWidget(sep)

		# ── Group: Grid Dimensions ────────────────────────────────────
		grp_dims = QGroupBox("Dimensi Grid (Jumlah Cell)")
		frm_dims = _form(grp_dims)
		self.nx_input = QSpinBox()
		self.ny_input = QSpinBox()
		self.nz_input = QSpinBox()
		for sb in (self.nx_input, self.ny_input, self.nz_input):
			sb.setRange(1, 1_000)
		frm_dims.addRow("NX  (arah X)", self.nx_input)
		frm_dims.addRow("NY  (arah Y)", self.ny_input)
		frm_dims.addRow("NZ  (arah Z)", self.nz_input)
		outer.addWidget(grp_dims)

		# ── Group: Cell Size ──────────────────────────────────────────
		grp_size = QGroupBox("Ukuran Cell")
		frm_size = _form(grp_size)
		self.dx_input = QDoubleSpinBox()
		self.dy_input = QDoubleSpinBox()
		self.dz_input = QDoubleSpinBox()
		for sb in (self.dx_input, self.dy_input, self.dz_input):
			sb.setRange(0.01, 1_000_000.0)
			sb.setDecimals(3)
			sb.setValue(1.0)
		frm_size.addRow("DX  (ft)", self.dx_input)
		frm_size.addRow("DY  (ft)", self.dy_input)
		frm_size.addRow("DZ  (ft)", self.dz_input)
		outer.addWidget(grp_size)

		# ── Grid summary info ─────────────────────────────────────────
		self._summary_label = QLabel()
		self._summary_label.setObjectName("pageHintLabel")
		self._summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		outer.addWidget(self._summary_label)

		outer.addStretch()

		# ── Wire signals ──────────────────────────────────────────────
		self.nx_input.valueChanged.connect(self._emit_change)
		self.ny_input.valueChanged.connect(self._emit_change)
		self.nz_input.valueChanged.connect(self._emit_change)
		self.dx_input.valueChanged.connect(self._emit_change)
		self.dy_input.valueChanged.connect(self._emit_change)
		self.dz_input.valueChanged.connect(self._emit_change)

		self._update_summary()

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
		self._update_summary()

	def _emit_change(self) -> None:
		self._update_summary()
		self.gridChanged.emit(
			self.nx_input.value(),
			self.ny_input.value(),
			self.nz_input.value(),
			self.dx_input.value(),
			self.dy_input.value(),
			self.dz_input.value(),
		)

	def _update_summary(self) -> None:
		nx, ny, nz = self.nx_input.value(), self.ny_input.value(), self.nz_input.value()
		dx, dy, dz = self.dx_input.value(), self.dy_input.value(), self.dz_input.value()
		total_cells = nx * ny * nz
		lx, ly, lz = nx * dx, ny * dy, nz * dz
		self._summary_label.setText(
			f"{nx} × {ny} × {nz} = {total_cells:,} sel  |  "
			f"{lx:,.1f} × {ly:,.1f} × {lz:,.1f} ft"
		)

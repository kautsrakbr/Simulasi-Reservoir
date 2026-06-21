from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
	QDoubleSpinBox,
	QFrame,
	QHBoxLayout,
	QLabel,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from windows.ui_kit import make_card, make_hero_banner

_AXIS_COLOR = {"X": "#ef4444", "Y": "#10b981", "Z": "#3b82f6"}
_AXIS_TINT = {"X": "#fef2f2", "Y": "#ecfdf5", "Z": "#eff6ff"}


def _axis_row(axis: str, label_text: str, spin: QWidget, suffix: str = "") -> QWidget:
	row = QWidget()
	row.setStyleSheet("background: transparent;")
	lay = QHBoxLayout(row)
	lay.setContentsMargins(0, 0, 0, 0)
	lay.setSpacing(10)

	color = _AXIS_COLOR[axis]
	tint = _AXIS_TINT[axis]
	badge = QLabel(axis)
	badge.setFixedSize(26, 26)
	badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
	badge.setStyleSheet(
		f"background-color: {tint}; color: {color}; border: 1.5px solid {color};"
		"border-radius: 13px; font-size: 9pt; font-weight: 800;"
	)
	lay.addWidget(badge)

	lbl = QLabel(label_text)
	lbl.setFixedWidth(120)
	lbl.setStyleSheet("font-size: 9pt; font-weight: 600; color: #5B6676;")
	lay.addWidget(lbl)

	spin.setMinimumHeight(32)
	lay.addWidget(spin, 1)

	if suffix:
		suf = QLabel(suffix)
		suf.setStyleSheet("font-size: 8.5pt; color: #93A1B2; font-weight: 700;")
		lay.addWidget(suf)

	return row


class GridPage(QWidget):
	gridChanged = Signal(int, int, int, float, float, float)

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setSpacing(14)
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

		# ── Hero stat banner ────────────────────────────────────────────
		self._summary_card, (self._stat_cells, self._stat_dims) = make_hero_banner(
			["TOTAL SEL", "DIMENSI TOTAL"]
		)
		outer.addWidget(self._summary_card)

		# ── Two-column input cards ────────────────────────────────────
		cards_row = QHBoxLayout()
		cards_row.setSpacing(14)

		card_dims, lay_dims = make_card("N", "#0F5C8E", "Dimensi Grid", "Jumlah cell pada tiap sumbu")
		self.nx_input = QSpinBox()
		self.ny_input = QSpinBox()
		self.nz_input = QSpinBox()
		for sb in (self.nx_input, self.ny_input, self.nz_input):
			sb.setRange(1, 1_000)
		lay_dims.addWidget(_axis_row("X", "Jumlah Cell X", self.nx_input))
		lay_dims.addWidget(_axis_row("Y", "Jumlah Cell Y", self.ny_input))
		lay_dims.addWidget(_axis_row("Z", "Jumlah Cell Z", self.nz_input))
		lay_dims.addStretch(1)
		cards_row.addWidget(card_dims, 1)

		card_size, lay_size = make_card("L", "#0F5C8E", "Ukuran Cell", "Dimensi fisik tiap cell (ft)")
		self.dx_input = QDoubleSpinBox()
		self.dy_input = QDoubleSpinBox()
		self.dz_input = QDoubleSpinBox()
		for sb in (self.dx_input, self.dy_input, self.dz_input):
			sb.setRange(0.01, 1_000_000.0)
			sb.setDecimals(3)
			sb.setValue(1.0)
		lay_size.addWidget(_axis_row("X", "Ukuran Cell X", self.dx_input, "ft"))
		lay_size.addWidget(_axis_row("Y", "Ukuran Cell Y", self.dy_input, "ft"))
		lay_size.addWidget(_axis_row("Z", "Ukuran Cell Z", self.dz_input, "ft"))
		lay_size.addStretch(1)
		cards_row.addWidget(card_size, 1)

		outer.addLayout(cards_row)
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
		self._stat_cells.setText(f"{nx} × {ny} × {nz}  =  {total_cells:,}")
		self._stat_dims.setText(f"{lx:,.1f} × {ly:,.1f} × {lz:,.1f} ft")

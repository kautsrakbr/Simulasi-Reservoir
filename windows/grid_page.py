from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QDoubleSpinBox,
	QFrame,
	QGraphicsDropShadowEffect,
	QHBoxLayout,
	QLabel,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig

_AXIS_COLOR = {"X": "#ef4444", "Y": "#10b981", "Z": "#3b82f6"}
_AXIS_TINT = {"X": "#fef2f2", "Y": "#ecfdf5", "Z": "#eff6ff"}

_SPIN_QSS = """
QSpinBox, QDoubleSpinBox {
	border: 1.5px solid #e2e8f0;
	border-radius: 8px;
	padding: 6px 10px;
	font-size: 9.5pt;
	font-weight: 700;
	color: #0f172a;
	background: #f8fafc;
}
QSpinBox:focus, QDoubleSpinBox:focus {
	border-color: #0891b2;
	background: #ffffff;
}
"""


def _card(icon_letter: str, icon_color: str, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
	card = QFrame()
	card.setObjectName("gridCard")
	card.setStyleSheet("""
		QFrame#gridCard {
			background-color: #ffffff;
			border: 1px solid #e2e8f0;
			border-radius: 12px;
		}
	""")
	shadow = QGraphicsDropShadowEffect(card)
	shadow.setBlurRadius(18)
	shadow.setColor(QColor(15, 23, 42, 22))
	shadow.setOffset(0, 3)
	card.setGraphicsEffect(shadow)

	lay = QVBoxLayout(card)
	lay.setContentsMargins(18, 16, 18, 16)
	lay.setSpacing(12)

	header = QHBoxLayout()
	header.setSpacing(10)

	icon_lbl = QLabel(icon_letter)
	icon_lbl.setFixedSize(32, 32)
	icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
	icon_lbl.setStyleSheet(
		f"background-color: {icon_color}; color: #ffffff; border-radius: 16px;"
		"font-size: 11pt; font-weight: 800;"
	)
	header.addWidget(icon_lbl)

	title_block = QVBoxLayout()
	title_block.setSpacing(0)
	title_lbl = QLabel(title)
	title_lbl.setStyleSheet("font-size: 11pt; font-weight: 800; color: #0f172a;")
	title_block.addWidget(title_lbl)
	sub_lbl = QLabel(subtitle)
	sub_lbl.setStyleSheet("font-size: 8pt; color: #94a3b8;")
	title_block.addWidget(sub_lbl)
	header.addLayout(title_block)
	header.addStretch(1)
	lay.addLayout(header)

	sep = QFrame()
	sep.setFrameShape(QFrame.Shape.HLine)
	sep.setStyleSheet("background-color: #f1f5f9; border: none; max-height: 1px;")
	lay.addWidget(sep)

	return card, lay


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
	lbl.setStyleSheet("font-size: 9pt; font-weight: 600; color: #475569;")
	lay.addWidget(lbl)

	spin.setStyleSheet(_SPIN_QSS)
	spin.setMinimumHeight(34)
	lay.addWidget(spin, 1)

	if suffix:
		suf = QLabel(suffix)
		suf.setStyleSheet("font-size: 8.5pt; color: #94a3b8; font-weight: 700;")
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
		self._summary_card = QFrame()
		self._summary_card.setObjectName("gridSummaryCard")
		self._summary_card.setStyleSheet("""
			QFrame#gridSummaryCard {
				background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
					stop:0 #06b6d4, stop:1 #0e7490);
				border-radius: 14px;
			}
		""")
		summary_shadow = QGraphicsDropShadowEffect(self._summary_card)
		summary_shadow.setBlurRadius(22)
		summary_shadow.setColor(QColor(8, 145, 178, 90))
		summary_shadow.setOffset(0, 5)
		self._summary_card.setGraphicsEffect(summary_shadow)

		sc_lay = QHBoxLayout(self._summary_card)
		sc_lay.setContentsMargins(22, 16, 22, 16)
		sc_lay.setSpacing(26)

		def _stat_block(tag: str) -> tuple[QVBoxLayout, QLabel]:
			block = QVBoxLayout()
			block.setSpacing(2)
			tag_lbl = QLabel(tag)
			tag_lbl.setStyleSheet(
				"font-size: 7.5pt; font-weight: 800; color: #cffafe;"
				"letter-spacing: 1.2px; background: transparent;"
			)
			block.addWidget(tag_lbl)
			val_lbl = QLabel("-")
			val_lbl.setStyleSheet(
				"font-size: 14pt; font-weight: 900; color: #ffffff; background: transparent;"
			)
			block.addWidget(val_lbl)
			return block, val_lbl

		block_cells, self._stat_cells = _stat_block("TOTAL SEL")
		block_dims, self._stat_dims = _stat_block("DIMENSI TOTAL")
		sc_lay.addLayout(block_cells)

		divider = QFrame()
		divider.setFrameShape(QFrame.Shape.VLine)
		divider.setStyleSheet("background-color: rgba(255,255,255,70); max-width: 1px;")
		sc_lay.addWidget(divider)

		sc_lay.addLayout(block_dims)
		sc_lay.addStretch(1)
		outer.addWidget(self._summary_card)

		# ── Two-column input cards ────────────────────────────────────
		cards_row = QHBoxLayout()
		cards_row.setSpacing(14)

		card_dims, lay_dims = _card("N", "#0891b2", "Dimensi Grid", "Jumlah cell pada tiap sumbu")
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

		card_size, lay_size = _card("L", "#0891b2", "Ukuran Cell", "Dimensi fisik tiap cell (ft)")
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

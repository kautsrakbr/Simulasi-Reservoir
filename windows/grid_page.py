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
from windows.ui_kit import make_card

_AXIS_COLOR = {"X": "#0C4A73", "Y": "#0F5C8E", "Z": "#2563A6"}


def _axis_row(axis: str, label_text: str, spin: QWidget, suffix: str = "") -> QWidget:
	row = QWidget()
	row.setStyleSheet("background: transparent;")
	lay = QHBoxLayout(row)
	lay.setContentsMargins(0, 0, 0, 0)
	lay.setSpacing(12)

	color = _AXIS_COLOR[axis]
	axis_lbl = QLabel(axis)
	axis_lbl.setFixedWidth(12)
	axis_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
	axis_lbl.setStyleSheet(
		f"font-size: 8.5pt; font-weight: 800; color: {color}; background: transparent;"
	)
	lay.addWidget(axis_lbl)

	lbl = QLabel(label_text)
	lbl.setFixedWidth(138)
	lbl.setStyleSheet("font-size: 9pt; font-weight: 600; color: #4F5D73;")
	lay.addWidget(lbl)

	spin.setMinimumHeight(32)
	lay.addWidget(spin, 1)

	if suffix:
		suf = QLabel(suffix)
		suf.setStyleSheet(f"font-size: 8.5pt; color: {color}; font-weight: 700;")
		lay.addWidget(suf)

	return row


def _summary_block(tag: str, note_text: str) -> tuple[QFrame, QLabel]:
	card = QFrame()
	card.setObjectName("gridSummaryCard")
	card.setStyleSheet("""
		QFrame#gridSummaryCard {
			background-color: #FFFFFF;
			border: 1px solid #D7DEE7;
			border-radius: 10px;
		}
		QFrame#gridSummaryCard QLabel {
			background: transparent;
		}
	""")
	card.setMinimumHeight(122)
	card.setMaximumHeight(136)
	lay = QVBoxLayout(card)
	lay.setContentsMargins(20, 14, 20, 14)
	lay.setSpacing(3)
	accent = QFrame()
	accent.setFixedHeight(3)
	accent.setStyleSheet("background:#DCEAF7; border:none; border-radius:1px;")
	lay.addWidget(accent)
	tag_lbl = QLabel(tag)
	tag_lbl.setStyleSheet(
		"font-size: 7.5pt; font-weight: 700; color: #5B6676;"
		"letter-spacing: 1.2px;"
	)
	val_lbl = QLabel("-")
	val_lbl.setStyleSheet(
		"font-size: 16pt; font-weight: 700; color: #0F5C8E;"
	)
	note_lbl = QLabel(note_text)
	note_lbl.setWordWrap(True)
	note_lbl.setStyleSheet("font-size: 8pt; color: #93A1B2;")
	lay.addWidget(tag_lbl)
	lay.addWidget(val_lbl)
	lay.addWidget(note_lbl)
	lay.addStretch(1)
	return card, val_lbl


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
		summary_row = QHBoxLayout()
		summary_row.setSpacing(14)
		card_cells, self._stat_cells = _summary_block("TOTAL SEL", "Konfigurasi jumlah cell pada sumbu X, Y, dan Z.")
		card_dims_total, self._stat_dims = _summary_block("DIMENSI TOTAL", "Panjang total reservoir hasil akumulasi ukuran cell.")
		summary_row.addWidget(card_cells, 1)
		summary_row.addWidget(card_dims_total, 1)
		outer.addLayout(summary_row)

		# ── Two-column input cards ────────────────────────────────────
		cards_row = QHBoxLayout()
		cards_row.setSpacing(14)

		card_dims, lay_dims = make_card("N", "#0F5C8E", "Dimensi Grid", "Jumlah cell pada tiap sumbu", show_icon=False)
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

		card_size, lay_size = make_card("L", "#0F5C8E", "Ukuran Cell", "Dimensi fisik tiap cell (ft)", show_icon=False)
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

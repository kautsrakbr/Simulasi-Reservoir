from __future__ import annotations

import math
from dataclasses import dataclass, field

from PySide6.QtCore import Qt, QPointF, QRect, QRectF, QSize, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen, QLinearGradient, QPolygonF
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QFrame,
	QGraphicsOpacityEffect,
	QGridLayout,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QLineEdit,
	QProgressBar,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QSlider,
	QSpinBox,
	QSplitter,
	QStackedWidget,
	QStyledItemDelegate,
	QTabWidget,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult, TimeStepResult
from engine.grid.builder import build_grid
from engine.physics.transmissibility import update_grid_transmissibility
from modules.results_service import get_run_summary, get_all_cell_properties
from windows.connectivity_3d_page import Connectivity3DPage, _Connectivity3DWidget


# ── Colormap Helper ───────────────────────────────────────────────────────────

def get_color_from_colormap(val: float, vmin: float, vmax: float, cmap: str) -> tuple[QColor, QColor]:
	"""
	Returns (bg_color, fg_text_color) for a value scaled between vmin and vmax.
	"""
	if vmax <= vmin:
		f = 0.0
	else:
		f = max(0.0, min(1.0, (val - vmin) / (vmax - vmin)))

	def interp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], fraction: float) -> tuple[int, int, int]:
		return (
			int(c1[0] + fraction * (c2[0] - c1[0])),
			int(c1[1] + fraction * (c2[1] - c1[1])),
			int(c1[2] + fraction * (c2[2] - c1[2])),
		)

	# Colormaps with stops matching workflow.ipynb Step 7
	if cmap == "Blues":
		rgb = interp_color((240, 248, 255), (13, 71, 161), f)
	elif cmap == "Greens":
		rgb = interp_color((232, 245, 233), (27, 94, 32), f)
	elif cmap == "YlOrRd":
		if f < 0.5:
			rgb = interp_color((255, 253, 231), (255, 152, 0), f * 2.0)
		else:
			rgb = interp_color((255, 152, 0), (213, 0, 0), (f - 0.5) * 2.0)
	elif cmap == "plasma":
		stops = [
			(13, 8, 135),
			(124, 2, 166),
			(203, 70, 121),
			(248, 148, 65),
			(240, 249, 33)
		]
		if f <= 0.25:
			rgb = interp_color(stops[0], stops[1], f / 0.25)
		elif f <= 0.5:
			rgb = interp_color(stops[1], stops[2], (f - 0.25) / 0.25)
		elif f <= 0.75:
			rgb = interp_color(stops[2], stops[3], (f - 0.5) / 0.25)
		else:
			rgb = interp_color(stops[3], stops[4], (f - 0.75) / 0.25)
	elif cmap == "viridis":
		stops = [
			(68, 1, 84),
			(49, 104, 142),
			(53, 183, 121),
			(144, 215, 67),
			(253, 231, 37)
		]
		if f <= 0.25:
			rgb = interp_color(stops[0], stops[1], f / 0.25)
		elif f <= 0.5:
			rgb = interp_color(stops[1], stops[2], (f - 0.25) / 0.25)
		elif f <= 0.75:
			rgb = interp_color(stops[2], stops[3], (f - 0.5) / 0.25)
		else:
			rgb = interp_color(stops[3], stops[4], (f - 0.75) / 0.25)
	elif cmap == "jet":
		stops = [
			(0, 0, 255),
			(0, 255, 255),
			(0, 255, 0),
			(255, 255, 0),
			(255, 0, 0),
		]
		if f <= 0.25:
			rgb = interp_color(stops[0], stops[1], f / 0.25)
		elif f <= 0.5:
			rgb = interp_color(stops[1], stops[2], (f - 0.25) / 0.25)
		elif f <= 0.75:
			rgb = interp_color(stops[2], stops[3], (f - 0.5) / 0.25)
		else:
			rgb = interp_color(stops[3], stops[4], (f - 0.75) / 0.25)
	elif cmap == "winter":
		rgb = interp_color((0, 0, 255), (0, 255, 128), f)
	elif cmap == "autumn":
		rgb = interp_color((255, 0, 0), (255, 255, 0), f)
	elif cmap == "hot":
		stops = [
			(10, 10, 10),
			(230, 0, 0),
			(255, 204, 0),
			(255, 255, 255)
		]
		if f <= 0.33:
			rgb = interp_color(stops[0], stops[1], f / 0.33)
		elif f <= 0.66:
			rgb = interp_color(stops[1], stops[2], (f - 0.33) / 0.33)
		else:
			rgb = interp_color(stops[2], stops[3], (f - 0.66) / 0.34)
	elif cmap == "cool":
		rgb = interp_color((0, 255, 255), (255, 0, 255), f)
	elif cmap == "copper":
		rgb = interp_color((0, 0, 0), (208, 112, 64), f)
	else:
		rgb = interp_color((13, 8, 135), (240, 249, 33), f)

	# Blend raw RGB with Slate Dark background (#1e293b: 30, 41, 59) to make it premium and non-garish
	blend_factor = 0.45
	r_blend = int(30 + blend_factor * (rgb[0] - 30))
	g_blend = int(41 + blend_factor * (rgb[1] - 41))
	b_blend = int(59 + blend_factor * (rgb[2] - 59))

	bg = QColor(r_blend, g_blend, b_blend)
	fg = QColor("#F7F9FB") # Clean off-white text for dark theme contrast

	return bg, fg


# Shared by the Table, Heatmap, and Per Waktu (time-lapse) sub-tabs so every
# view formats a given property identically.
PROP_VALUE_FORMATS: dict[str, str] = {
	"pressure_psia": "{:.2f}",
	"so": "{:.5f}", "sw": "{:.5f}", "sg": "{:.5f}",
	"bo": "{:.6f}", "bw": "{:.6f}", "bg": "{:.6f}",
	"mu_o": "{:.5f}", "mu_w": "{:.5f}", "mu_g": "{:.5f}",
	"kro": "{:.5f}", "krw": "{:.5f}", "krg": "{:.5f}",
	"lam_o": "{:.6f}", "lam_w": "{:.6f}", "lam_g": "{:.6f}",
	"rho_o": "{:.3f}", "rho_w": "{:.3f}", "rho_g": "{:.3f}",
	"pcow": "{:.4f}", "pcgw": "{:.4f}",
}

# Colormap presets the user can pick for the grid heatmap. "None" means
# "use the recommended colormap for the selected property".
COLORMAP_CHOICES: list[tuple[str, str | None]] = [
	("Default (Sesuai Properti)", None),
	("Plasma", "plasma"),
	("Viridis", "viridis"),
	("Jet (Rainbow)", "jet"),
	("Blues", "Blues"),
	("Greens", "Greens"),
	("Yellow-Orange-Red", "YlOrRd"),
	("Hot", "hot"),
	("Cool", "cool"),
	("Winter", "winter"),
	("Autumn", "autumn"),
	("Copper", "copper"),
]


# ── Colorbar Widget ───────────────────────────────────────────────────────────

class _ColorbarWidget(QWidget):
	def __init__(self, parent: QWidget | None = None, orientation: Qt.Orientation = Qt.Orientation.Horizontal) -> None:
		super().__init__(parent)
		self._orientation = orientation
		if orientation == Qt.Orientation.Vertical:
			self.setFixedWidth(74)
			self.setMinimumHeight(140)
			self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
		else:
			self.setMinimumHeight(45)
		self.vmin = 0.0
		self.vmax = 1.0
		self.cmap = "plasma"
		self.label = ""

	def set_scale(self, vmin: float, vmax: float, cmap: str, label: str) -> None:
		self.vmin = vmin
		self.vmax = vmax
		self.cmap = cmap
		self.label = label
		self.update()

	@staticmethod
	def _fmt(val: float) -> str:
		return f"{val:.4e}" if abs(val) < 1e-2 or abs(val) >= 1e4 else f"{val:.4f}"

	def paintEvent(self, event) -> None:
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		if self._orientation == Qt.Orientation.Vertical:
			self._paint_vertical(painter)
		else:
			self._paint_horizontal(painter)
		painter.end()

	def _paint_horizontal(self, painter: QPainter) -> None:
		w = self.width()

		font = QFont("Segoe UI", 8)
		painter.setFont(font)
		painter.setPen(QColor("#5B6676"))

		title = f"Skala: {self.label}"
		painter.drawText(QRectF(0, 0, w, 15), Qt.AlignmentFlag.AlignCenter, title)

		bar_y = 17
		bar_h = 12
		bar_margin = 15
		bar_w = w - 2 * bar_margin

		grad = QLinearGradient(bar_margin, 0, bar_margin + bar_w, 0)
		n_stops = 10
		for i in range(n_stops + 1):
			frac = i / n_stops
			val = self.vmin + frac * (self.vmax - self.vmin)
			bg_color, _ = get_color_from_colormap(val, self.vmin, self.vmax, self.cmap)
			grad.setColorAt(frac, bg_color)

		painter.setBrush(QBrush(grad))
		painter.setPen(QPen(QColor("#D7DEE7"), 1))
		painter.drawRect(bar_margin, bar_y, bar_w, bar_h)

		painter.setPen(QColor("#1F2937"))
		painter.drawText(QRectF(bar_margin, bar_y + bar_h + 2, 100, 12), Qt.AlignmentFlag.AlignLeft, self._fmt(self.vmin))
		painter.drawText(QRectF(w - bar_margin - 100, bar_y + bar_h + 2, 100, 12), Qt.AlignmentFlag.AlignRight, self._fmt(self.vmax))

	def _paint_vertical(self, painter: QPainter) -> None:
		w = self.width()
		h = self.height()

		bar_x = 10
		bar_w = 14
		label_h = 16
		bar_margin = label_h
		bar_h = h - 2 * bar_margin
		if bar_h <= 10:
			return

		grad = QLinearGradient(0, bar_margin, 0, bar_margin + bar_h)
		n_stops = 10
		for i in range(n_stops + 1):
			frac = i / n_stops
			val = self.vmin + frac * (self.vmax - self.vmin)
			bg_color, _ = get_color_from_colormap(val, self.vmin, self.vmax, self.cmap)
			# Top of the bar = vmax, bottom = vmin (standard vertical colorbar convention).
			grad.setColorAt(1.0 - frac, bg_color)

		painter.setBrush(QBrush(grad))
		painter.setPen(QPen(QColor("#D7DEE7"), 1))
		painter.drawRect(bar_x, bar_margin, bar_w, bar_h)

		painter.setFont(QFont("Segoe UI", 7))
		painter.setPen(QColor("#1F2937"))
		text_rect_w = w - bar_x
		painter.drawText(QRectF(bar_x - 2, 0, text_rect_w, label_h), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self._fmt(self.vmax))
		painter.drawText(QRectF(bar_x - 2, bar_margin + bar_h, text_rect_w, label_h), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._fmt(self.vmin))


# ── Heatmap Cell Widget ────────────────────────────────────────────────────────

class _HeatmapCellWidget(QFrame):
	def __init__(self, cell_num: int, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.cell_num = cell_num
		self.setObjectName("heatmapCell")

		lay = QVBoxLayout(self)
		lay.setContentsMargins(4, 6, 4, 6)
		lay.setSpacing(4)

		self.lbl_num = QLabel(f"C{cell_num}", self)
		self.lbl_num.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.lbl_val = QLabel("-", self)
		self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

		lay.addWidget(self.lbl_num)
		lay.addWidget(self.lbl_val)

	def update_cell(self, value: float, bg_color: QColor, fg_color: QColor, fmt_str: str, w: int, h: int) -> None:
		self.setFixedSize(w, h)
		num_text = f"C{self.cell_num}"
		val_text = fmt_str.format(value)
		available_w = max(w - 10, 10)

		# Scale fonts based on cell dimensions, then shrink further (and elide
		# as a last resort) until the text actually fits -- never let digits
		# get clipped by the cell's rounded border.
		fs_num = 10 if w >= 100 else (8 if w >= 75 else 7)
		fs_val = 11 if w >= 100 else (9 if w >= 75 else 8)

		font_num = QFont("Segoe UI", fs_num)
		font_num.setBold(True)
		while fs_num > 6 and QFontMetrics(font_num).horizontalAdvance(num_text) > available_w:
			fs_num -= 1
			font_num.setPointSize(fs_num)
		if QFontMetrics(font_num).horizontalAdvance(num_text) > available_w:
			num_text = QFontMetrics(font_num).elidedText(num_text, Qt.TextElideMode.ElideRight, available_w)
		self.lbl_num.setText(num_text)

		font_val = QFont("Segoe UI", fs_val)
		font_val.setBold(True)
		while fs_val > 6 and QFontMetrics(font_val).horizontalAdvance(val_text) > available_w:
			fs_val -= 1
			font_val.setPointSize(fs_val)
		if QFontMetrics(font_val).horizontalAdvance(val_text) > available_w:
			val_text = QFontMetrics(font_val).elidedText(val_text, Qt.TextElideMode.ElideRight, available_w)
		self.lbl_val.setText(val_text)

		bg_hex = bg_color.name()
		fg_hex = fg_color.name()
		fg_dim = f"rgba({fg_color.red()}, {fg_color.green()}, {fg_color.blue()}, 175)"

		# Soft hairline border (instead of a heavy dark outline) so the grid
		# reads as a continuous tile sheet rather than boxed-in squares.
		self.setStyleSheet(f"""
			QFrame#heatmapCell {{
				background-color: {bg_hex};
				border: 1px solid rgba(255, 255, 255, 70);
				border-radius: 10px;
			}}
		""")
		# font-size must be set here (inline, per-instance QSS) rather than via
		# .setFont() -- the app-level stylesheet's "QWidget { font-size: 10pt }"
		# rule otherwise silently overrides any programmatic font set on a
		# QLabel, which was clipping these dynamically-sized cell values.
		self.lbl_num.setStyleSheet(
			f"color: {fg_dim}; background: transparent; font-size: {fs_num}pt; font-weight: 700;"
		)
		self.lbl_val.setStyleSheet(
			f"color: {fg_hex}; background: transparent; font-size: {fs_val}pt; font-weight: 700;"
		)


# ── Per Waktu (time-lapse) panel ──────────────────────────────────────────────

@dataclass
class _MultiStepPanel:
	"""One property heatmap inside the Per Waktu tab's side-by-side comparison."""

	combo: QComboBox
	grid_layout: QGridLayout
	colorbar: "_ColorbarWidget"
	title_label: QLabel
	cell_widgets: dict[int, "_HeatmapCellWidget"] = field(default_factory=dict)


# ── Pure functions ────────────────────────────────────────────────────────────

def _symmetric_cells(n: int, well: int, nx: int, ny: int) -> list[int]:
	"""Return 1-indexed cells symmetric to n about well in the XY plane.

	Uses 8-way offset transforms around the well:
	- sign flips: (dr, dc), (-dr, dc), (dr, -dc), (-dr, -dc)
	- axis swap : (dc, dr) and its sign flips

	This captures cases like well=1 where cell 2 is symmetric with cell 6.
	"""
	nr, nc = divmod(n - 1, nx)
	wr, wc = divmod(well - 1, nx)
	dr, dc = nr - wr, nc - wc
	result: set[int] = set()
	for tr, tc in [
		(dr, dc),
		(-dr, dc),
		(dr, -dc),
		(-dr, -dc),
		(dc, dr),
		(-dc, dr),
		(dc, -dr),
		(-dc, -dr),
	]:
		r2, c2 = wr + tr, wc + tc
		if 0 <= r2 < ny and 0 <= c2 < nx:
			m = r2 * nx + c2 + 1
			if m != n:
				result.add(m)
	return sorted(result)


_SYMMETRY_TRANSFORM_CODES = (
	"same",
	"flip_r",
	"flip_c",
	"flip_rc",
	"swap",
	"swap_flip_r",
	"swap_flip_c",
	"swap_flip_rc",
)


def _transform_offset(dr: int, dc: int, code: str) -> tuple[int, int]:
	if code == "same":
		return dr, dc
	if code == "flip_r":
		return -dr, dc
	if code == "flip_c":
		return dr, -dc
	if code == "flip_rc":
		return -dr, -dc
	if code == "swap":
		return dc, dr
	if code == "swap_flip_r":
		return -dc, dr
	if code == "swap_flip_c":
		return dc, -dr
	if code == "swap_flip_rc":
		return -dc, -dr
	raise ValueError(f"Unknown symmetry transform code: {code}")


def _apply_symmetry_transform(cell: int, well: int, nx: int, ny: int, code: str) -> int | None:
	row, col = divmod(cell - 1, nx)
	well_row, well_col = divmod(well - 1, nx)
	dr, dc = row - well_row, col - well_col
	tr, tc = _transform_offset(dr, dc, code)
	row2, col2 = well_row + tr, well_col + tc
	if 0 <= row2 < ny and 0 <= col2 < nx:
		return row2 * nx + col2 + 1
	return None


def _symmetry_transform_code_for_pair(n: int, s: int, well: int, nx: int, ny: int) -> str | None:
	for code in _SYMMETRY_TRANSFORM_CODES:
		mapped = _apply_symmetry_transform(n, well, nx, ny, code)
		if mapped == s:
			return code
	return None



def _residuals_close(v1: float, v2: float, rtol: float = 1e-4) -> bool:
	denom = max(abs(v1), abs(v2), 1e-30)
	return abs(v1 - v2) / denom < rtol


def _repolish(widget: QWidget) -> None:
	widget.style().unpolish(widget)
	widget.style().polish(widget)


def _icon_badge(letter: str, color: str, size: int = 20) -> QLabel:
	"""Small circular colored badge with a letter, matching the icon-badge cards used elsewhere in the app."""
	lbl = QLabel(letter)
	lbl.setFixedSize(size, size)
	lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
	lbl.setStyleSheet(
		f"background-color: {color}; color: #ffffff; border-radius: {size // 2}px; "
		f"font-size: {max(7, int(size * 0.48))}px; font-weight: 800;"
	)
	return lbl


def _title_row(title_label: QLabel, icon: str, color: str) -> QHBoxLayout:
	"""Wrap an existing title QLabel. Icons intentionally omitted for a cleaner validation UI."""
	del icon, color
	row = QHBoxLayout()
	row.setContentsMargins(0, 0, 0, 0)
	row.setSpacing(0)
	row.addWidget(title_label, 1)
	return row


def _make_card(title: str, icon: str | None = None, color: str = "#0F5C8E") -> tuple[QFrame, QLabel]:
	"""Return (card QFrame, title QLabel)."""
	card = QFrame()
	card.setObjectName("resultCard")
	lay = QVBoxLayout(card)
	lay.setContentsMargins(14, 10, 14, 12)
	lay.setSpacing(6)
	hdr_row = QHBoxLayout()
	hdr_row.setContentsMargins(0, 0, 0, 0)
	hdr_row.setSpacing(8)
	del icon, color
	hdr = QLabel(title.upper())
	hdr.setObjectName("resultCardTitle")
	hdr_row.addWidget(hdr, 1)
	sep = QFrame()
	sep.setFrameShape(QFrame.Shape.HLine)
	sep.setObjectName("resultCardSep")
	lay.addLayout(hdr_row)
	lay.addWidget(sep)
	return card, hdr


def _add_row(card: QFrame, label: str, value: str) -> QLabel:
	row = QHBoxLayout()
	row.setContentsMargins(0, 0, 0, 0)
	lbl_w = QLabel(label)
	lbl_w.setObjectName("resultRowLabel")
	lbl_w.setFixedWidth(70)
	val_w = QLabel(value)
	val_w.setObjectName("resultRowValue")
	val_w.setWordWrap(True)
	row.addWidget(lbl_w)
	row.addWidget(val_w, 1)
	card.layout().addLayout(row)
	return val_w


def _make_stat_card(title: str, icon: str | None = None, color: str = "#0F5C8E") -> tuple[QFrame, QLabel]:
	card = QFrame()
	card.setObjectName("resultStatCard")
	lay = QVBoxLayout(card)
	lay.setContentsMargins(12, 10, 12, 10)
	lay.setSpacing(4)
	title_row = QHBoxLayout()
	title_row.setContentsMargins(0, 0, 0, 0)
	title_row.setSpacing(6)
	del icon, color
	title_lbl = QLabel(title)
	title_lbl.setObjectName("resultStatTitle")
	title_row.addWidget(title_lbl, 1)
	value_lbl = QLabel("-")
	value_lbl.setObjectName("resultStatValue")
	value_lbl.setWordWrap(True)
	lay.addLayout(title_row)
	lay.addWidget(value_lbl)
	return card, value_lbl


def _clear_layout(lay: QVBoxLayout) -> None:
	while lay.count():
		item = lay.takeAt(0)
		if item.widget():
			item.widget().deleteLater()


class _SortableTableItem(QTableWidgetItem):
	def __init__(self, text: str, sort_value: object) -> None:
		super().__init__(text)
		self._sort_value = sort_value

	def __lt__(self, other) -> bool:
		if isinstance(other, _SortableTableItem):
			return self._sort_value < other._sort_value
		return super().__lt__(other)


# ── Norm Chart ────────────────────────────────────────────────────────────────

class _NormChartWidget(QWidget):
	"""QPainter-based line chart: Norm vs Step."""

	_COLOR_LINE  = QColor("#2E7DAE")
	_COLOR_OK    = QColor("#2D6A4F")
	_COLOR_FAIL  = QColor("#B2413F")
	_COLOR_GRID  = QColor("#1a1c24")
	_COLOR_AXIS  = QColor("#8a8f9e")
	_COLOR_BG    = QColor("#0e0f14")
	_COLOR_PLOT  = QColor("#121319")
	_COLOR_BORDER = QColor("#2d313f")

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._data: list[tuple[int, float, bool]] = []
		self.setMinimumHeight(170)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	def set_data(self, data: list[tuple[int, float, bool]]) -> None:
		self._data = data
		self.update()

	def paintEvent(self, event) -> None:  # noqa: N802
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		w, h = self.width(), self.height()
		ml, mr, mt, mb = 62, 18, 14, 36
		px0, px1 = ml, w - mr
		py0, py1 = mt, h - mb
		pw, ph   = px1 - px0, py1 - py0

		# backgrounds
		painter.fillRect(self.rect(), self._COLOR_BG)
		painter.fillRect(px0, py0, pw, ph, self._COLOR_PLOT)
		painter.setPen(QPen(self._COLOR_BORDER, 1))
		painter.drawRect(px0, py0, pw, ph)

		if not self._data:
			painter.setPen(self._COLOR_AXIS)
			painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Belum ada data")
			painter.end()
			return

		steps = [d[0] for d in self._data]
		norms = [d[1] for d in self._data]
		oks   = [d[2] for d in self._data]

		step_min, step_max = min(steps), max(steps)
		norm_min, norm_max = min(norms), max(norms)
		step_rng = max(step_max - step_min, 1)
		norm_rng = max(norm_max - norm_min, norm_max * 0.1, 1e-30)
		nd_min = max(0.0, norm_min - norm_rng * 0.12)
		nd_max = norm_max + norm_rng * 0.12
		nd_rng = nd_max - nd_min

		def to_pt(step: int, norm: float) -> QPointF:
			sx = px0 + (step - step_min) / step_rng * pw if step_rng else px0 + pw / 2
			sy = py1 - (norm - nd_min) / nd_rng * ph
			return QPointF(sx, sy)

		# ── y-grid and axis labels ────────────────────────────────────────────
		font = QFont()
		font.setPointSize(7)
		painter.setFont(font)
		grid_pen = QPen(self._COLOR_GRID, 1, Qt.PenStyle.DashLine)
		n_ticks = 4
		for i in range(n_ticks + 1):
			frac   = i / n_ticks
			y_val  = nd_min + nd_rng * frac
			py_tick = py1 - frac * ph
			painter.setPen(grid_pen)
			painter.drawLine(QPointF(px0, py_tick), QPointF(px1, py_tick))
			painter.setPen(self._COLOR_AXIS)
			painter.drawText(
				QRectF(0, py_tick - 10, ml - 5, 20),
				Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
				f"{y_val:.2e}",
			)

		# ── x-axis labels (step numbers) ──────────────────────────────────────
		painter.setPen(self._COLOR_AXIS)
		for step in steps:
			px_tick = to_pt(step, 0).x()
			painter.drawText(
				QRectF(px_tick - 20, py1 + 4, 40, 18),
				Qt.AlignmentFlag.AlignCenter,
				str(step),
			)
		# x-axis title
		font_ax = QFont()
		font_ax.setPointSize(7)
		font_ax.setItalic(True)
		painter.setFont(font_ax)
		painter.drawText(
			QRectF(px0, py1 + 20, pw, 14),
			Qt.AlignmentFlag.AlignCenter,
			"Step",
		)

		# ── line ─────────────────────────────────────────────────────────────
		painter.setPen(QPen(self._COLOR_LINE, 2))
		for i in range(len(self._data) - 1):
			painter.drawLine(to_pt(steps[i], norms[i]), to_pt(steps[i + 1], norms[i + 1]))

		# ── dots ─────────────────────────────────────────────────────────────
		for step, norm, ok in self._data:
			pt = to_pt(step, norm)
			color = self._COLOR_OK if ok else self._COLOR_FAIL
			painter.setBrush(QBrush(color))
			painter.setPen(QPen(QColor("#ffffff"), 1.5))
			painter.drawEllipse(pt, 5, 5)

		# ── y-axis label ──────────────────────────────────────────────────────
		painter.save()
		font_y = QFont()
		font_y.setPointSize(7)
		font_y.setItalic(True)
		painter.setFont(font_y)
		painter.setPen(self._COLOR_AXIS)
		painter.translate(10, py0 + ph / 2)
		painter.rotate(-90)
		painter.drawText(QRectF(-40, -10, 80, 20), Qt.AlignmentFlag.AlignCenter, "Norm")
		painter.restore()

		painter.end()


# ── Newton-Raphson Concept Diagram ────────────────────────────────────────────
class _NewtonConceptDiagram(QWidget):
	"""Illustrative 1D Newton-Raphson diagram: r(x) vs x, tangent lines, root
	approach. Not driven by real run data — r(x) = 0.04*(x-1)^3 + 0.1*(x-1) is
	a fixed convex curve picked purely so the tangent-line story is visible."""

	_COLOR_CURVE  = QColor("#2E7DAE")
	_COLOR_TANGENT = QColor("#D98C2B")
	_COLOR_AXIS   = QColor("#8a8f9e")
	_COLOR_POINT  = QColor("#B2413F")
	_COLOR_BG     = QColor("#0e0f14")
	_COLOR_PLOT   = QColor("#121319")
	_COLOR_BORDER = QColor("#2d313f")
	_X_ROOT = 1.0
	_X0 = 5.0

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setMinimumHeight(260)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	@classmethod
	def _r(cls, x: float) -> float:
		dx = x - cls._X_ROOT
		return 0.04 * dx ** 3 + 0.1 * dx

	@classmethod
	def _dr(cls, x: float) -> float:
		dx = x - cls._X_ROOT
		return 0.12 * dx ** 2 + 0.1

	@classmethod
	def _newton_step(cls, x: float) -> float:
		return x - cls._r(x) / cls._dr(x)

	def paintEvent(self, event) -> None:  # noqa: N802
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		w, h = self.width(), self.height()
		ml, mr, mt, mb = 50, 24, 20, 40
		px0, px1 = ml, w - mr
		py0, py1 = mt, h - mb
		pw, ph = px1 - px0, py1 - py0

		painter.fillRect(self.rect(), self._COLOR_BG)
		painter.fillRect(px0, py0, pw, ph, self._COLOR_PLOT)
		painter.setPen(QPen(self._COLOR_BORDER, 1))
		painter.drawRect(px0, py0, pw, ph)

		x_min, x_max = -0.4, self._X0 + 0.4
		x0 = self._X0
		x1 = self._newton_step(x0)
		x2 = self._newton_step(x1)

		samples = [x_min + (x_max - x_min) * i / 200 for i in range(201)]
		r_values = [self._r(x) for x in samples]
		y_min, y_max = min(r_values + [0.0]), max(r_values)
		y_rng = max(y_max - y_min, 1e-6)
		x_rng = max(x_max - x_min, 1e-6)

		def to_pt(x: float, y: float) -> QPointF:
			sx = px0 + (x - x_min) / x_rng * pw
			sy = py1 - (y - y_min) / y_rng * ph
			return QPointF(sx, sy)

		# r = 0 axis
		painter.setPen(QPen(self._COLOR_AXIS, 1, Qt.PenStyle.DashLine))
		painter.drawLine(to_pt(x_min, 0.0), to_pt(x_max, 0.0))
		painter.setPen(self._COLOR_AXIS)
		painter.drawText(QRectF(px1 - 60, to_pt(x_max, 0.0).y() - 18, 56, 16), Qt.AlignmentFlag.AlignRight, "r = 0")

		# curve r(x)
		painter.setPen(QPen(self._COLOR_CURVE, 2.2))
		for i in range(len(samples) - 1):
			painter.drawLine(to_pt(samples[i], r_values[i]), to_pt(samples[i + 1], r_values[i + 1]))
		painter.setPen(self._COLOR_CURVE)
		painter.drawText(to_pt(x_min, r_values[0]) + QPointF(4, -6), "r(x)")

		# tangent at x0 -> x1, and x1 -> x2
		tangent_pen = QPen(self._COLOR_TANGENT, 1.6, Qt.PenStyle.DashLine)
		for idx, (xa, xb) in enumerate(((x0, x1), (x1, x2))):
			painter.setPen(tangent_pen)
			painter.drawLine(to_pt(xa, self._r(xa)), to_pt(xb, 0.0))
			mid = to_pt((xa + xb) / 2, self._r(xa) / 2)
			painter.setPen(self._COLOR_TANGENT)
			painter.drawText(mid + QPointF(-30, -8), f"∂r/∂x|k={idx}")

		# points x0, x1, x2
		labels = [("x(k=0)", x0, self._r(x0)), ("x(k=1)", x1, self._r(x1)), ("x(k+1)", x2, self._r(x2))]
		for label, x, y in labels:
			pt = to_pt(x, y)
			painter.setBrush(QBrush(self._COLOR_POINT))
			painter.setPen(QPen(QColor("#ffffff"), 1.2))
			painter.drawEllipse(pt, 4.5, 4.5)
			axis_pt = to_pt(x, 0.0)
			painter.setPen(QPen(self._COLOR_AXIS, 1, Qt.PenStyle.DotLine))
			painter.drawLine(pt, axis_pt)
			painter.setPen(self._COLOR_AXIS)
			painter.drawText(QRectF(axis_pt.x() - 30, py1 + 6, 60, 16), Qt.AlignmentFlag.AlignCenter, label)

		font_ax = QFont()
		font_ax.setPointSize(7)
		font_ax.setItalic(True)
		painter.setFont(font_ax)
		painter.setPen(self._COLOR_AXIS)
		painter.drawText(QRectF(px0, py1 + 22, pw, 14), Qt.AlignmentFlag.AlignCenter, "x (representasi p, Sw, atau Sg)")

		painter.end()


# ── Newton vs Quasi-Newton comparison card ────────────────────────────────────
class _ComparisonCard(QFrame):
	"""Mirrors methods_page._MethodCard's dim-when-inactive look, but driven
	by whether a run result exists for this method rather than a selection."""

	def __init__(self, title: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("comparisonCard")
		self._opacity = QGraphicsOpacityEffect(self)
		self.setGraphicsEffect(self._opacity)

		root = QVBoxLayout(self)
		root.setContentsMargins(20, 18, 20, 18)
		root.setSpacing(10)

		title_row = QHBoxLayout()
		self._title = QLabel(title)
		self._title.setObjectName("methodCardTitle")
		self._badge = QLabel("Belum di-Run")
		self._badge.setObjectName("methodCardSummary")
		title_row.addWidget(self._title)
		title_row.addStretch()
		title_row.addWidget(self._badge)
		root.addLayout(title_row)

		self._rows: dict[str, QLabel] = {}
		for key, caption in (
			("iterations", "Total Iterasi Newton"),
			("elapsed", "CPU Time"),
			("steps", "Jumlah Step"),
			("converged", "Step Konvergen"),
		):
			row = QHBoxLayout()
			cap = QLabel(caption)
			cap.setObjectName("methodBodyText")
			val = QLabel("—")
			val.setObjectName("resultRowValue")
			row.addWidget(cap)
			row.addStretch()
			row.addWidget(val)
			root.addLayout(row)
			self._rows[key] = val

		root.addStretch(1)
		self.set_result(None)

	def set_result(self, run_result: RunResult | None) -> None:
		has_result = run_result is not None
		self._opacity.setOpacity(1.0 if has_result else 0.44)
		self._badge.setText("Sudah di-Run" if has_result else "Belum di-Run")
		if not has_result:
			for label in self._rows.values():
				label.setText("—")
			return
		total_iterations = sum(step.summary.newton_iterations for step in run_result.steps)
		converged_count = sum(1 for step in run_result.steps if step.summary.converged)
		self._rows["iterations"].setText(str(total_iterations))
		self._rows["elapsed"].setText(f"{run_result.total_elapsed_seconds:.3f} s")
		self._rows["steps"].setText(str(len(run_result.steps)))
		self._rows["converged"].setText(f"{converged_count}/{len(run_result.steps)}")


# ── Correction Chart Widget ───────────────────────────────────────────────────

class _CorrectionChartWidget(QWidget):
	"""QPainter-based bar chart displaying Newton corrections per cell."""
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setMinimumHeight(240)
		self.dp: list[float] = []
		self.dsw: list[float] = []
		self.dsg: list[float] = []

	def set_data(self, dp: list[float], dsw: list[float], dsg: list[float]) -> None:
		self.dp = dp
		self.dsw = dsw
		self.dsg = dsg
		self.update()

	def paintEvent(self, event) -> None:
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		w = self.width()
		h = self.height()

		# Draw Background
		painter.fillRect(self.rect(), QColor("#0e0f14"))

		if not self.dp:
			font = QFont("Segoe UI", 9)
			painter.setFont(font)
			painter.setPen(QColor("#5B6676"))
			painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Belum ada data koreksi")
			painter.end()
			return

		n_cells = len(self.dp)
		# Draw 3 stacked subplots: dp, dsw, dsg
		margin_l = 75
		margin_r = 15
		margin_t = 15
		margin_b = 30

		sub_h = (h - margin_t - margin_b) / 3
		plot_w = w - margin_l - margin_r

		colors = {
			"dp": QColor("#0F5C8E"),  # Pressure (petroleum-blue accent)
			"dsw": QColor("#2563A6"), # Water saturation (info-blue)
			"dsg": QColor("#0F766E"), # Gas saturation (gas-teal)
		}

		datasets = [
			(self.dp, "δp (psia)", colors["dp"]),
			(self.dsw, "δSw (frac)", colors["dsw"]),
			(self.dsg, "δSg (frac)", colors["dsg"]),
		]

		for idx, (data, title, color) in enumerate(datasets):
			sy0 = margin_t + idx * sub_h
			sy1 = sy0 + sub_h - 8
			sh = sy1 - sy0

			# Draw panel box
			painter.setPen(QPen(QColor("#2d313f"), 1))
			painter.setBrush(QBrush(QColor("#121319")))
			painter.drawRect(margin_l, sy0, plot_w, sh)

			# Find min/max for scale
			max_val = max((abs(v) for v in data), default=0.0)
			limit = max(max_val * 1.1, 1e-4)

			# Zero line
			zero_y = sy0 + sh / 2
			painter.setPen(QPen(QColor("#1a1c24"), 1, Qt.PenStyle.DashLine))
			painter.drawLine(margin_l, zero_y, margin_l + plot_w, zero_y)

			# Draw bars
			bar_width = max(2.0, (plot_w / n_cells) * 0.7)
			gap = (plot_w / n_cells) * 0.3

			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(QBrush(color))

			for c_idx, val in enumerate(data):
				bx = margin_l + c_idx * (plot_w / n_cells) + gap / 2
				bar_h_pixels = (val / limit) * (sh / 2)

				if bar_h_pixels >= 0:
					painter.drawRect(bx, zero_y - bar_h_pixels, bar_width, bar_h_pixels)
				else:
					painter.drawRect(bx, zero_y, bar_width, -bar_h_pixels)

			# Draw labels
			font = QFont("Segoe UI", 7)
			painter.setFont(font)
			painter.setPen(QColor("#93A1B2"))

			# Title label
			painter.drawText(QRectF(10, sy0, margin_l - 15, sh), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, title)

			# Draw limits
			painter.drawText(QRectF(margin_l + 4, sy0 + 2, 80, 12), Qt.AlignmentFlag.AlignLeft, f"+{limit:.2e}")
			painter.drawText(QRectF(margin_l + 4, sy1 - 12, 80, 12), Qt.AlignmentFlag.AlignLeft, f"-{limit:.2e}")

		# Draw cell indices on bottom axis
		painter.setPen(QColor("#5B6676"))
		font = QFont("Segoe UI", 7)
		painter.setFont(font)
		for c_idx in range(n_cells):
			bx = margin_l + c_idx * (plot_w / n_cells) + (plot_w / n_cells) / 2
			painter.drawText(QRectF(bx - 15, h - margin_b + 4, 30, 15), Qt.AlignmentFlag.AlignCenter, str(c_idx + 1))

		painter.drawText(QRectF(margin_l, h - 15, plot_w, 15), Qt.AlignmentFlag.AlignCenter, "Nomor Sel")
		painter.end()


# ── Jacobian constants ────────────────────────────────────────────────────────

_JACOBIAN_ZOOM_STEPS       = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.75, 1.00, 1.25, 1.50, 2.00, 2.50, 3.00, 4.00)
_JACOBIAN_ZOOM_DEFAULT_IDX = 9
_JAC_DIAG_COMPONENTS = (
	("p", "Ro-p", 0, 0),
	("sw", "Rw-Sw", 1, 1),
	("sg", "Rg-Sg", 2, 2),
)


# ── Jacobian Canvas (zero-bug pure-QPainter renderer) ─────────────────────────

class _JacobianCanvas(QWidget):
	"""
	Renders the Jacobian matrix with QPainter in a single coordinate system.
	Eliminates all QHeaderView alignment bugs. Wrap in QScrollArea.
	"""

	# ── sizes at zoom = 1.0 ─────────────────────────────────────────────────
	_CW  = 82   # data column width
	_RH  = 25   # data row height
	_CGH = 22   # column group header height  ("Cell N")
	_CPH = 18   # column phase header height  ("P / Sw / Sg")
	_RGW = 40   # row group header width      ("Cell N")
	_RPW = 30   # row phase header width      ("Ro / Rw / Rg")
	_FNT = 8    # base font size

	# ── color palette ────────────────────────────────────────────────────────
	_C_BG      = "#0d1117"   # canvas / zero cell
	_C_HDR     = "#161b22"   # phase-header band
	_C_GRP     = "#1e3a5f"   # group-header band (navy)
	_C_GRID    = "#30363d"   # minor grid line (slightly brighter → readable at tiny zoom)
	_C_SEP     = "#ffffff"   # major group separator (white)
	_C_GRP_TXT = "#93c5fd"   # "Cell N" text
	_C_PH_TXT  = "#bfdbfe"   # "P / Sw / Sg" / "Ro / Rw / Rg" text
	_C_ZERO    = "#484f58"   # zero-value text
	_C_LO_TXT  = "#e6edf3"   # value text on dark cell
	_C_HI_TXT  = "#0d1117"   # value text on bright cell

	# Well row/column highlight — amber, matching the "well" color used elsewhere
	# (e.g. the Connectivity/Jacobian 3D grid's well-cell marker).
	_C_WELL = "#A86A15"

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._data:   list[list[float]] = []
		self._nc      = 0      # number of cell groups (= n_cells)
		self._zoom    = 1.0
		self._maxabs  = 0.0
		self._well_idx: int | None = None   # 0-indexed cell group with an active well

	# ── public API ───────────────────────────────────────────────────────────

	def set_data(self, data: list[list[float]], n_cells: int,
	             zoom: float = 1.0, well_cell: int | None = None) -> None:
		self._data   = data
		self._nc     = n_cells
		self._zoom   = zoom
		self._maxabs = max((abs(v) for row in data for v in row), default=0.0)
		self._well_idx = (well_cell - 1) if well_cell else None
		self.updateGeometry()
		self.adjustSize()   # QScrollArea.setWidget() doesn't auto-apply sizeHint changes
		self.update()

	def set_zoom(self, zoom: float) -> None:
		self._zoom = zoom
		self.updateGeometry()
		self.adjustSize()   # QScrollArea.setWidget() doesn't auto-apply sizeHint changes
		self.update()

	# ── geometry ─────────────────────────────────────────────────────────────

	def _D(self) -> dict:
		z = self._zoom
		return {
			"cw":  max(8,  int(self._CW  * z)),
			"rh":  max(4,  int(self._RH  * z)),
			"cgh": max(3,  int(self._CGH * z)),
			"cph": max(2,  int(self._CPH * z)),
			"rgw": max(4,  int(self._RGW * z)),
			"rpw": max(3,  int(self._RPW * z)),
			"fs":  max(5,  int(self._FNT * z)),
			"sw":  max(1,  round(2 * z)),
		}

	def sizeHint(self) -> QSize:
		if not self._data:
			return QSize(400, 200)
		D = self._D();  n = len(self._data)
		return QSize(D["rgw"] + D["rpw"] + n * D["cw"] + 2,
		             D["cgh"] + D["cph"] + n * D["rh"] + 2)

	def minimumSizeHint(self) -> QSize:
		return self.sizeHint()

	def natural_size(self) -> QSize:
		"""Size at zoom = 1.0, used to compute a fit-to-viewport zoom factor."""
		n = len(self._data)
		if n == 0:
			return QSize(400, 200)
		return QSize(self._RGW + self._RPW + n * self._CW + 2,
		             self._CGH + self._CPH + n * self._RH + 2)

	# ── paint ────────────────────────────────────────────────────────────────

	def paintEvent(self, ev) -> None:
		p = QPainter(self)
		p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
		p.fillRect(self.rect(), QColor(self._C_BG))

		if not self._data:
			p.setPen(QColor(self._C_ZERO))
			p.setFont(QFont("Segoe UI", 10))
			p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Tidak ada data")
			p.end()
			return

		D  = self._D()
		cw, rh   = D["cw"],  D["rh"]
		cgh, cph = D["cgh"], D["cph"]
		rgw, rpw = D["rgw"], D["rpw"]
		fs, sw   = D["fs"],  D["sw"]
		n        = len(self._data)
		nc       = self._nc
		ox       = rgw + rpw
		oy       = cgh + cph
		tw       = ox + n * cw
		th       = oy + n * rh

		f_grp  = QFont("Segoe UI Variable Text", max(5, fs));  f_grp.setBold(True)
		f_ph   = QFont("Segoe UI Variable Text", max(4, fs - 1));  f_ph.setBold(True)
		f_data = QFont("Consolas", fs)

		PHASES_C = ("P", "Sw", "Sg")
		PHASES_R = ("Ro", "Rw", "Rg")

		# text is only legible above these thresholds
		show_grp_lbl  = cgh >= 8 and cw * 3 >= 24
		show_ph_lbl   = cph >= 7 and cw >= 12
		show_data_txt = cw >= 22 and rh >= 9

		# ── Column headers ─────────────────────────────────────────────────
		for c in range(n):
			xi  = ox + c * cw
			phi = c % 3
			ci  = c // 3
			# Phase label (lower band)
			pr = QRect(xi, cgh, cw, cph)
			p.fillRect(pr, QColor(self._C_HDR))
			p.setPen(QPen(QColor(self._C_GRID), 1))
			p.drawRect(pr.adjusted(0, 0, -1, -1))
			if show_ph_lbl:
				p.setFont(f_ph);  p.setPen(QColor(self._C_PH_TXT))
				p.drawText(pr, Qt.AlignmentFlag.AlignCenter, PHASES_C[phi])
			# Group label (upper band, full 3-col span, drawn once)
			if phi == 0:
				gr = QRect(xi, 0, cw * 3, cgh)
				p.fillRect(gr, QColor(self._C_GRP))
				if show_grp_lbl:
					p.setFont(f_grp);  p.setPen(QColor(self._C_GRP_TXT))
					p.drawText(gr, Qt.AlignmentFlag.AlignCenter, f"Cell {ci + 1}")

		# ── Row headers ────────────────────────────────────────────────────
		for r in range(n):
			yi  = oy + r * rh
			phi = r % 3
			ci  = r // 3
			# Phase label (right band)
			pr = QRect(rgw, yi, rpw, rh)
			p.fillRect(pr, QColor(self._C_HDR))
			p.setPen(QPen(QColor(self._C_GRID), 1))
			p.drawRect(pr.adjusted(0, 0, -1, -1))
			if show_ph_lbl:
				p.setFont(f_ph);  p.setPen(QColor(self._C_PH_TXT))
				p.drawText(pr, Qt.AlignmentFlag.AlignCenter, PHASES_R[phi])
			# Group label (left band, full 3-row span, drawn once)
			if phi == 0:
				gr = QRect(0, yi, rgw, rh * 3)
				p.fillRect(gr, QColor(self._C_GRP))
				if show_grp_lbl:
					p.setFont(f_grp);  p.setPen(QColor(self._C_GRP_TXT))
					p.drawText(gr, Qt.AlignmentFlag.AlignCenter, f"Cell {ci + 1}")

		# ── Corner ────────────────────────────────────────────────────────
		p.fillRect(0, 0, ox, oy, QColor(self._C_GRP))

		# ── Data cells ────────────────────────────────────────────────────
		if show_data_txt:
			p.setFont(f_data)
		for r in range(n):
			yi = oy + r * rh
			for c in range(n):
				xi  = ox + c * cw
				val = self._data[r][c]
				bg, fg = self._cell_color(val)
				p.fillRect(QRect(xi, yi, cw, rh), bg)
				p.setPen(QPen(QColor(self._C_GRID), 1))
				p.drawRect(QRect(xi, yi, cw - 1, rh - 1))
				if show_data_txt:
					lbl = f"{val:.3e}" if abs(val) > 1e-30 else "0"
					p.setPen(fg)
					p.drawText(QRect(xi, yi, cw, rh),
					           Qt.AlignmentFlag.AlignCenter, lbl)

		# ── Major separators (cell-group boundaries) ───────────────────────
		p.setPen(QPen(QColor(self._C_SEP), sw))
		for i in range(1, nc):
			x = ox + i * 3 * cw
			p.drawLine(x, 0, x, th)
			y = oy + i * 3 * rh
			p.drawLine(0, y, tw, y)

		# Outer frame
		p.setBrush(Qt.BrushStyle.NoBrush)
		p.setPen(QPen(QColor(self._C_SEP), sw))
		p.drawRect(0, 0, tw - 1, th - 1)

		# ── Well row/column highlight ──────────────────────────────────────
		if self._well_idx is not None and 0 <= self._well_idx < nc:
			p.setBrush(Qt.BrushStyle.NoBrush)
			p.setPen(QPen(QColor(self._C_WELL), max(2, sw + 1)))
			wx = ox + self._well_idx * 3 * cw
			wy = oy + self._well_idx * 3 * rh
			p.drawRect(wx, 0, 3 * cw, th - 1)
			p.drawRect(0, wy, tw - 1, 3 * rh)
			if show_grp_lbl:
				p.setPen(QColor(self._C_WELL))
				p.setFont(f_grp)
				p.drawText(QRect(wx, 0, 3 * cw, cgh), Qt.AlignmentFlag.AlignCenter, f"● Cell {self._well_idx + 1} (WELL)")

		p.end()

	def _cell_color(self, val: float) -> tuple[QColor, QColor]:
		ma = self._maxabs
		if ma <= 0.0 or abs(val) < 1e-30:
			return QColor(self._C_BG), QColor(self._C_ZERO)

		t = math.sqrt(abs(val) / ma)

		def li(a: int, b: int, f: float) -> int:
			return max(0, min(255, int(a + f * (b - a))))

		if val > 0:
			# dark navy  →  sky-blue
			if t < 0.5:
				f = t * 2
				r, g, b = li(0x0a, 0x1e, f), li(0x1a, 0x4c, f), li(0x2e, 0x8a, f)
			else:
				f = (t - 0.5) * 2
				r, g, b = li(0x1e, 0x02, f), li(0x4c, 0x84, f), li(0x8a, 0xc7, f)
		else:
			# dark maroon  →  crimson
			if t < 0.5:
				f = t * 2
				r, g, b = li(0x1e, 0x7f, f), li(0x0d, 0x1d, f), li(0x0d, 0x1d, f)
			else:
				f = (t - 0.5) * 2
				r, g, b = li(0x7f, 0xef, f), li(0x1d, 0x44, f), li(0x1d, 0x44, f)

		bg = QColor(r, g, b)
		br = 0.299 * r + 0.587 * g + 0.114 * b
		fg = QColor(self._C_HI_TXT) if br > 120 else QColor(self._C_LO_TXT)
		return bg, fg




class _AutoFitScrollArea(QScrollArea):
	"""QScrollArea that emits `resized` so its content can refit to the new viewport."""

	resized = Signal()

	def resizeEvent(self, event) -> None:
		super().resizeEvent(event)
		self.resized.emit()


class ValidationPage(QWidget):
	"""Validation viewer — grid symmetry checker, residual bars, convergence log, Newton-Raphson vs quasi-Newton comparison."""

	goToRunRequested = Signal()

	def __init__(self) -> None:
		super().__init__()
		self._nx = 2
		self._ny = 1
		self.project_config: ProjectConfig | None = None
		self._run_result: RunResult | None = None
		self._active_run_result: RunResult | None = None  # alias for retry table
		self._selected_cell: int | None = None
		self._well_cell: int = 1
		self._cell_btns: dict[int, QPushButton] = {}
		self._prop_cell_widgets: dict[int, _HeatmapCellWidget] = {}
		self._multistep_panels: list[_MultiStepPanel] = []
		self._multistep_global_ranges: dict[str, tuple[float, float]] = {}
		self._multistep_timer = QTimer(self)
		self._multistep_timer.setInterval(700)
		self._multistep_timer.timeout.connect(self._multistep_timer_tick)
		self._jac_sym_selected_cell: int | None = None
		self._jac_sym_btns: dict[int, QPushButton] = {}
		self._grid_connection_3d_page = Connectivity3DPage(show_bottom_controls=False, detail_mode="cell_diagnostics")

		# ── Header ──────────────────────────────────────────────────────────
		self._header = QWidget(self)
		self._header.setObjectName("resultHeader")
		_hrow = QHBoxLayout(self._header)
		_hrow.setContentsMargins(20, 14, 20, 14)
		_hrow.setSpacing(10)
		_title = QLabel("Validation", self._header)
		_title.setObjectName("resultTitle")
		self._badge = QLabel("", self._header)
		self._badge.setObjectName("resultBadge")
		self._badge.setProperty("status", "empty")
		self._badge.hide()
		_go_run = QPushButton("Go to Run", self._header)
		_go_run.setObjectName("resultActionButton")
		_go_run.setFixedWidth(100)
		_go_run.setCursor(Qt.CursorShape.PointingHandCursor)
		_go_run.clicked.connect(self.goToRunRequested)
		_hrow.addWidget(_title)
		_hrow.addStretch(1)
		_hrow.addWidget(_go_run)

		# ── Groups ───────────────────────────────────────────────────────────
		# Top-level group selection lives in the sidebar (Validation section in
		# main_window.py), not as an in-page tab bar — this is a plain stacked
		# widget switched via show_group().
		self._tabs = QStackedWidget(self)
		self._tabs.setObjectName("resultGroupStack")

		self._tabs.addWidget(self._build_summary_tab())

		residual_check_tabs = self._make_group_tabs()
		residual_check_tabs.addTab(self._build_residual_tab(), "  Residual  ")
		residual_check_tabs.addTab(self._build_conv_tab(), "  Konvergensi  ")
		residual_check_tabs.addTab(self._build_retry_tab(), "  Retry Log  ")
		self._tabs.addWidget(residual_check_tabs)

		grid_connection_tabs = self._make_group_tabs()
		grid_connection_tabs.addTab(self._build_grid_tab(), "  Connection List  ")
		grid_connection_tabs.addTab(self._grid_connection_3d_page, "  Grid Property  ")
		grid_connection_tabs.addTab(self._build_properties_tab(), "  Peta Properti  ")
		self._tabs.addWidget(grid_connection_tabs)

		jacobian_tabs = self._make_group_tabs()
		jacobian_tabs.addTab(self._build_jacobian_tab(), "  Jacobian  ")
		jacobian_tabs.addTab(self._build_jacobian_symmetry_tab(), "  Simetri Jacobian  ")
		jacobian_tabs.addTab(self._build_corrections_tab(), "  Koreksi Newton  ")
		self._tabs.addWidget(jacobian_tabs)

		self._tabs.addWidget(self._build_comparison_tab())

		# ── Root layout ──────────────────────────────────────────────────────
		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(self._tabs, 1)

		# Wire signals
		self.retry_scope_combo.currentIndexChanged.connect(self._refresh_retry_table)
		self.retry_status_combo.currentIndexChanged.connect(self._refresh_retry_table)
		if hasattr(self, "_well_spin"):
			self._well_spin.valueChanged.connect(self._on_well_changed)

		# Build initial grid
		self._rebuild_grid()

	# =========================================================================
	# Tab builders
	# =========================================================================

	def _make_group_tabs(self) -> QTabWidget:
		group = QTabWidget()
		group.setObjectName("resultGroupTabs")
		group.tabBar().setObjectName("resultGroupTabBar")
		group.tabBar().setExpanding(False)
		group.setDocumentMode(True)
		return group

	def _build_grid_tab_placeholder(self) -> QWidget:
		"""Grid Property placeholder — Connection List already owns the live
		self._grid_* widgets, so this can't just call _build_grid_tab() again
		(that would silently steal those attributes from the real tab). Stays
		a static notice until Grid Property gets its own dedicated view."""
		w = QWidget()
		w.setObjectName("resultGridPropertyPlaceholder")
		lay = QVBoxLayout(w)
		lay.setContentsMargins(20, 20, 20, 20)
		lay.setSpacing(8)
		notice = QLabel(
			"Sama seperti Connection List untuk saat ini — tampilan Grid Property "
			"akan dirombak terpisah di task berikutnya."
		)
		notice.setWordWrap(True)
		notice.setObjectName("resultRowLabel")
		lay.addWidget(notice)
		lay.addStretch(1)
		return w

	def _build_grid_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultGridTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(0, 0, 0, 0)
		vlay.setSpacing(0)

		# Controls row
		toolbar = QWidget(w)
		toolbar.setObjectName("resultToolbar")
		ctrl = QHBoxLayout(toolbar)
		ctrl.setContentsMargins(16, 8, 16, 8)
		ctrl.setSpacing(14)
		title = QLabel("Connection List")
		title.setObjectName("pageTitle")
		title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #0F5C8E;")
		ctrl.addWidget(title)
		self._grid_hint = QLabel("Pilih cell untuk melihat koneksi langsungnya.")
		self._grid_hint.setObjectName("resultStatusLine")
		ctrl.addWidget(self._grid_hint, 1)
		for kind, text in [
			("symmetric", "Connected"),
			("selected", "Dipilih"),
		]:
			dot = QFrame()
			dot.setObjectName("resultLegendDot")
			dot.setProperty("kind", kind)
			dot.setFixedSize(12, 12)
			ctrl.addWidget(dot)
			legend_lbl = QLabel(text)
			legend_lbl.setObjectName("resultLegendLabel")
			ctrl.addWidget(legend_lbl)
		vlay.addWidget(toolbar)

		# Splitter: left = isometric grid, right = connection cards
		splitter = QSplitter(Qt.Orientation.Horizontal)
		splitter.setHandleWidth(6)
		splitter.setChildrenCollapsible(False)

		self._grid_scroll = QScrollArea()
		self._grid_scroll.setObjectName("resultGridScroll")
		self._grid_scroll.setWidgetResizable(True)
		self._grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
		self._grid_container = QWidget()
		self._grid_container.setObjectName("resultGridPanel")
		self._grid_layout = QGridLayout(self._grid_container)
		self._grid_layout.setSpacing(8)
		self._grid_layout.setContentsMargins(16, 16, 16, 16)
		self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self._grid_scroll.setWidget(self._grid_container)

		left_w = QWidget()
		left_lay = QVBoxLayout(left_w)
		left_lay.setContentsMargins(12, 12, 6, 12)
		left_lay.setSpacing(0)
		left_lay.addWidget(self._grid_scroll, 1)
		left_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

		splitter.addWidget(left_w)

		right_w = QWidget()
		right_w.setObjectName("resultInfoPanel")
		right_w.setMinimumWidth(320)
		right_w.setMaximumWidth(460)
		right_lay = QVBoxLayout(right_w)
		right_lay.setContentsMargins(8, 12, 12, 12)
		right_lay.setSpacing(10)

		self._sel_card, self._sel_card_title = _make_card("Selected Cell: —", icon="S", color="#0F5C8E")
		self._lbl_sel_p   = _add_row(self._sel_card, "Pressure", "—")
		self._lbl_sel_sw  = _add_row(self._sel_card, "Sw", "—")
		self._lbl_sel_sg  = _add_row(self._sel_card, "Sg", "—")
		self._lbl_sel_res = _add_row(self._sel_card, "Connected", "—")
		right_lay.addWidget(self._sel_card)

		self._sym_card, _ = _make_card("Cell Connections", icon="C", color="#2D6A4F")
		self._sym_body = QVBoxLayout()
		self._sym_body.setSpacing(5)
		_h = QLabel("Pilih cell pada grid untuk melihat koneksi langsung berdasarkan grid model.")
		_h.setObjectName("resultRowLabel")
		_h.setWordWrap(True)
		self._sym_body.addWidget(_h)
		self._sym_card.layout().addLayout(self._sym_body)
		right_lay.addWidget(self._sym_card)

		right_lay.addStretch(1)
		splitter.addWidget(right_w)
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 0)
		splitter.setSizes([720, 360])
		vlay.addWidget(splitter, 1)
		return w



	def _build_residual_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultResidualTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(14, 12, 14, 14)
		vlay.setSpacing(10)

		# ── Toolbar row ──────────────────────────────────────────────────────
		toolbar = QWidget()
		toolbar.setObjectName("resultToolbar")
		tbar_lay = QHBoxLayout(toolbar)
		tbar_lay.setContentsMargins(12, 8, 12, 8)
		tbar_lay.setSpacing(10)

		self._resid_status = QLabel("Jalankan simulasi dulu.")
		self._resid_status.setObjectName("resultStatusLine")
		self._resid_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		tbar_lay.addWidget(self._resid_status, 1)

		self._resid_conv_badge = QLabel("—")
		self._resid_conv_badge.setObjectName("resultBadge")
		self._resid_conv_badge.setProperty("status", "empty")
		tbar_lay.addWidget(self._resid_conv_badge)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(step_lbl)

		self._resid_step_combo = QComboBox()
		self._resid_step_combo.setObjectName("resultResidStepCombo")
		self._resid_step_combo.setMinimumWidth(140)
		self._resid_step_combo.currentIndexChanged.connect(self._on_resid_step_changed)
		tbar_lay.addWidget(self._resid_step_combo)

		vlay.addWidget(toolbar)

		# ── Per-phase max-residual summary chips ──────────────────────────────
		chips_row = QHBoxLayout()
		chips_row.setContentsMargins(0, 0, 0, 0)
		chips_row.setSpacing(10)
		self._resid_phase_lbls: dict[str, QLabel] = {}
		for key, name, icon, color in (
			("oil",   "Oil",   "O", "#B7791F"),
			("water", "Water", "W", "#2563A6"),
			("gas",   "Gas",   "G", "#0F766E"),
		):
			chip = QFrame()
			chip.setObjectName("resultCard")
			chip_lay = QVBoxLayout(chip)
			chip_lay.setContentsMargins(12, 8, 12, 9)
			chip_lay.setSpacing(3)
			name_lbl = QLabel(f"MAX RESIDUAL — {name.upper()}")
			name_lbl.setObjectName("resultCardTitle")
			chip_lay.addLayout(_title_row(name_lbl, icon, color))
			value_lbl = QLabel("—")
			value_lbl.setStyleSheet(
				f"font-family: Consolas; font-size: 13pt; font-weight: 800; color: {color};"
			)
			chip_lay.addWidget(value_lbl)
			self._resid_phase_lbls[key] = value_lbl
			chips_row.addWidget(chip, 1)
		vlay.addLayout(chips_row)

		# ── Unified residual table ────────────────────────────────────────────
		card = QFrame()
		card.setObjectName("resultCard")
		card_lay = QVBoxLayout(card)
		card_lay.setContentsMargins(12, 10, 12, 10)
		card_lay.setSpacing(6)

		card_title = QLabel("RESIDUAL PER SEL")
		card_title.setObjectName("resultCardTitle")
		title_row = _title_row(card_title, "R", "#0F5C8E")
		title_row.addStretch(1)
		legend = QLabel(
			'<span style="color:#2563A6;">●</span> Positif&nbsp;&nbsp;'
			'<span style="color:#B2413F;">●</span> Negatif&nbsp;&nbsp;'
			'<span style="color:#93A1B2;">●</span> ≈ 0'
		)
		legend.setObjectName("resultLegendLabel")
		title_row.addWidget(legend)
		card_lay.addLayout(title_row)

		self._resid_table = QTableWidget()
		self._resid_table.setObjectName("dataTable")
		self._resid_table.setColumnCount(4)
		self._resid_table.setHorizontalHeaderLabels(
			["Sel", "Residual Oil", "Residual Water", "Residual Gas"]
		)
		self._resid_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self._resid_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self._resid_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self._resid_table.verticalHeader().setVisible(False)
		self._resid_table.verticalHeader().setDefaultSectionSize(30)
		rh = self._resid_table.horizontalHeader()
		rh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
		self._resid_table.setColumnWidth(0, 62)
		for col in (1, 2, 3):
			rh.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
		self._resid_table.setAlternatingRowColors(True)
		card_lay.addWidget(self._resid_table, 1)
		vlay.addWidget(card, 1)
		return w

	def _build_conv_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultConvTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(14, 12, 14, 14)
		vlay.setSpacing(10)

		# Status line
		self._conv_status = QLabel("Jalankan simulasi dulu.")
		self._conv_status.setObjectName("resultStatusLine")
		vlay.addWidget(self._conv_status)

		# Splitter: table (top) | chart (bottom)
		splitter = QSplitter(Qt.Orientation.Vertical)
		splitter.setHandleWidth(6)
		splitter.setChildrenCollapsible(False)

		# ── Table card ───────────────────────────────────────────────────
		table_card = QFrame()
		table_card.setObjectName("resultCard")
		tc_lay = QVBoxLayout(table_card)
		tc_lay.setContentsMargins(12, 10, 12, 10)
		tc_lay.setSpacing(6)
		tc_title = QLabel("RIWAYAT KONVERGENSI NEWTON")
		tc_title.setObjectName("resultCardTitle")
		tc_lay.addLayout(_title_row(tc_title, "K", "#2563A6"))

		self._conv_table = QTableWidget()
		self._conv_table.setObjectName("dataTable")
		self._conv_table.setColumnCount(7)
		self._conv_table.setHorizontalHeaderLabels(
			["Step", "t (hari)", "dt (hari)", "Iterasi", "MaxR", "Norm", "Status"]
		)
		self._conv_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self._conv_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self._conv_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self._conv_table.verticalHeader().setVisible(False)
		self._conv_table.setAlternatingRowColors(True)
		hh = self._conv_table.horizontalHeader()
		hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		for col in (0, 3):
			hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
		hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
		self._conv_table.setColumnWidth(6, 110)
		tc_lay.addWidget(self._conv_table, 1)
		splitter.addWidget(table_card)

		# ── Chart card ───────────────────────────────────────────────────
		chart_card = QFrame()
		chart_card.setObjectName("resultCard")
		cc_lay = QVBoxLayout(chart_card)
		cc_lay.setContentsMargins(12, 10, 12, 10)
		cc_lay.setSpacing(6)
		cc_title = QLabel("KONVERGENSI  NORM vs STEP")
		cc_title.setObjectName("resultCardTitle")
		cc_lay.addLayout(_title_row(cc_title, "N", "#08395A"))
		self._conv_chart = _NormChartWidget()
		cc_lay.addWidget(self._conv_chart, 1)
		splitter.addWidget(chart_card)

		splitter.setSizes([320, 220])
		vlay.addWidget(splitter, 1)
		return w

	# =========================================================================
	# Jacobian Matrix tab
	# =========================================================================

	def _build_jacobian_tab(self) -> QWidget:
		self._jacobian_zoom_idx = _JACOBIAN_ZOOM_DEFAULT_IDX
		self._jacobian_autofit  = True

		w = QWidget()
		w.setObjectName("resultJacobianTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(0, 0, 0, 0)
		vlay.setSpacing(0)

		# ── Toolbar ───────────────────────────────────────────────────
		toolbar = QWidget()
		toolbar.setObjectName("resultToolbar")
		tbar_lay = QHBoxLayout(toolbar)
		tbar_lay.setContentsMargins(12, 8, 12, 8)
		tbar_lay.setSpacing(8)

		self._jacobian_status = QLabel("Jalankan simulasi dulu.")
		self._jacobian_status.setObjectName("resultStatusLine")
		self._jacobian_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		tbar_lay.addWidget(self._jacobian_status, 1)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(step_lbl)

		self.jacobian_step_combo = QComboBox()
		self.jacobian_step_combo.setObjectName("resultJacobianStepCombo")
		self.jacobian_step_combo.setMinimumWidth(140)
		self.jacobian_step_combo.currentIndexChanged.connect(self._on_jacobian_step_changed)
		tbar_lay.addWidget(self.jacobian_step_combo)

		tbar_lay.addSpacing(16)

		self.btn_jacobian_fit = QPushButton("⛶  Fit Layar")
		self.btn_jacobian_fit.setObjectName("resultJacobianFitBtn")
		self.btn_jacobian_fit.setCheckable(True)
		self.btn_jacobian_fit.setChecked(True)
		self.btn_jacobian_fit.setCursor(Qt.CursorShape.PointingHandCursor)
		self.btn_jacobian_fit.setToolTip("Sesuaikan matriks otomatis ke ukuran jendela")
		self.btn_jacobian_fit.clicked.connect(self._on_jacobian_fit_toggled)
		tbar_lay.addWidget(self.btn_jacobian_fit)

		zoom_lbl = QLabel("Zoom:")
		zoom_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(zoom_lbl)

		btn_zoom_out = QPushButton("−")
		btn_zoom_out.setObjectName("resultToolbarBtn")
		btn_zoom_out.setFixedWidth(28)
		btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_zoom_out.setToolTip("Zoom out")
		btn_zoom_out.clicked.connect(self._jacobian_zoom_out)
		tbar_lay.addWidget(btn_zoom_out)

		self._jacobian_zoom_label = QLabel("100%")
		self._jacobian_zoom_label.setObjectName("resultToolbarLabel")
		self._jacobian_zoom_label.setFixedWidth(44)
		self._jacobian_zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		tbar_lay.addWidget(self._jacobian_zoom_label)

		btn_zoom_in = QPushButton("+")
		btn_zoom_in.setObjectName("resultToolbarBtn")
		btn_zoom_in.setFixedWidth(28)
		btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_zoom_in.setToolTip("Zoom in")
		btn_zoom_in.clicked.connect(self._jacobian_zoom_in)
		tbar_lay.addWidget(btn_zoom_in)

		btn_zoom_reset = QPushButton("↺")
		btn_zoom_reset.setObjectName("resultToolbarBtn")
		btn_zoom_reset.setFixedWidth(28)
		btn_zoom_reset.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_zoom_reset.setToolTip("Reset zoom")
		btn_zoom_reset.clicked.connect(self._jacobian_zoom_reset)
		tbar_lay.addWidget(btn_zoom_reset)

		vlay.addWidget(toolbar)

		# ── Canvas inside a scroll area ───────────────────────────────
		self._jacobian_canvas = _JacobianCanvas()

		scroll = _AutoFitScrollArea()
		scroll.setObjectName("resultJacobianScroll")
		scroll.setWidget(self._jacobian_canvas)
		scroll.setWidgetResizable(False)   # canvas owns its sizeHint
		scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
		scroll.resized.connect(self._on_jacobian_viewport_resized)
		self._jacobian_scroll = scroll

		vlay.addWidget(scroll, 1)
		return w

	def _build_jacobian_symmetry_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultJacobianSymmetryTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(12, 10, 12, 12)
		vlay.setSpacing(8)

		toolbar = QWidget(w)
		toolbar.setObjectName("resultToolbar")
		ctrl = QHBoxLayout(toolbar)
		ctrl.setContentsMargins(12, 9, 12, 9)
		ctrl.setSpacing(12)

		self._jac_sym_status = QLabel("Jalankan simulasi dulu.")
		self._jac_sym_status.setObjectName("resultStatusLine")
		self._jac_sym_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		ctrl.addWidget(self._jac_sym_status, 1)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		ctrl.addWidget(step_lbl)

		self._jac_sym_step_combo = QComboBox()
		self._jac_sym_step_combo.setMinimumWidth(140)
		self._jac_sym_step_combo.currentIndexChanged.connect(self._populate_jacobian_symmetry)
		ctrl.addWidget(self._jac_sym_step_combo)

		well_lbl = QLabel("Well cell:")
		well_lbl.setObjectName("resultToolbarLabel")
		ctrl.addWidget(well_lbl)

		self._jac_sym_well_spin = QSpinBox()
		self._jac_sym_well_spin.setRange(1, 9999)
		self._jac_sym_well_spin.setFixedWidth(80)
		self._jac_sym_well_spin.valueChanged.connect(self._on_jacobian_sym_well_changed)
		ctrl.addWidget(self._jac_sym_well_spin)

		for kind, text in [("well", "Well"), ("selected", "Dipilih"), ("symmetric", "Simetris")]:
			dot = QFrame()
			dot.setObjectName("resultLegendDot")
			dot.setProperty("kind", kind)
			dot.setFixedSize(12, 12)
			ctrl.addWidget(dot)
			legend_lbl = QLabel(text)
			legend_lbl.setObjectName("resultLegendLabel")
			ctrl.addWidget(legend_lbl)

		vlay.addWidget(toolbar)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		splitter.setHandleWidth(6)
		splitter.setChildrenCollapsible(False)

		self._jac_sym_grid_scroll = QScrollArea()
		self._jac_sym_grid_scroll.setObjectName("resultGridScroll")
		self._jac_sym_grid_scroll.setWidgetResizable(True)
		self._jac_sym_grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
		self._jac_sym_grid_container = QWidget()
		self._jac_sym_grid_container.setObjectName("resultGridPanel")
		self._jac_sym_grid_layout = QGridLayout(self._jac_sym_grid_container)
		self._jac_sym_grid_layout.setSpacing(4)
		self._jac_sym_grid_layout.setContentsMargins(8, 8, 8, 8)
		self._jac_sym_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
		self._jac_sym_grid_scroll.setWidget(self._jac_sym_grid_container)

		self._jac_sym_hint = QLabel("Pilih sel untuk melihat simetri baris pressure Jacobian plus diagonal blok 3x3: Ro-p, Rw-Sw, dan Rg-Sg.")
		self._jac_sym_hint.setObjectName("resultGridHint")
		self._jac_sym_hint.setWordWrap(True)

		left_w = QWidget()
		left_lay = QVBoxLayout(left_w)
		left_lay.setContentsMargins(0, 0, 0, 0)
		left_lay.setSpacing(8)
		left_lay.addWidget(self._jac_sym_hint)
		left_lay.addWidget(self._jac_sym_grid_scroll, 1)
		splitter.addWidget(left_w)

		right_w = QWidget()
		right_w.setObjectName("resultInfoPanel")
		right_w.setMinimumWidth(300)
		right_w.setMaximumWidth(450)
		right_lay = QVBoxLayout(right_w)
		right_lay.setContentsMargins(4, 0, 0, 0)
		right_lay.setSpacing(10)

		self._jac_sym_sel_card, self._jac_sym_sel_title = _make_card("Diag Cell Jacobian: —", icon="J", color="#0F5C8E")
		self._jac_sym_diag = _add_row(self._jac_sym_sel_card, "Diag p", "—")
		self._jac_sym_diag_sw = _add_row(self._jac_sym_sel_card, "Diag Sw", "—")
		self._jac_sym_diag_sg = _add_row(self._jac_sym_sel_card, "Diag Sg", "—")
		self._jac_sym_well = _add_row(self._jac_sym_sel_card, "Well p", "—")
		self._jac_sym_rowmax = _add_row(self._jac_sym_sel_card, "Max diag", "—")
		right_lay.addWidget(self._jac_sym_sel_card)

		self._jac_sym_card, _ = _make_card("Cek Simetri Jacobian", icon="S", color="#2D6A4F")
		self._jac_sym_body = QVBoxLayout()
		self._jac_sym_body.setSpacing(5)
		placeholder = QLabel("Pilih sel untuk membandingkan simetri pressure row dan diag cell p/Sw/Sg.")
		placeholder.setObjectName("resultRowLabel")
		placeholder.setWordWrap(True)
		self._jac_sym_body.addWidget(placeholder)
		self._jac_sym_card.layout().addLayout(self._jac_sym_body)
		right_lay.addWidget(self._jac_sym_card)
		right_lay.addStretch(1)

		splitter.addWidget(right_w)
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 0)
		splitter.setSizes([700, 340])
		vlay.addWidget(splitter, 1)

		self._rebuild_jacobian_sym_grid()
		return w

	def _on_jacobian_step_changed(self) -> None:
		self._populate_jacobian_display()
		self._populate_jacobian_symmetry()

	def _populate_jacobian_display(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._jacobian_canvas.set_data([], 0)
			return

		idx = self.jacobian_step_combo.currentIndex()
		if idx < 0 or idx >= len(self._run_result.steps):
			return
		step = self._run_result.steps[idx]

		jacobian = getattr(step, "jacobian", [])
		if not jacobian:
			self._jacobian_canvas.set_data([], 0)
			self._jacobian_status.setText(
				f"Step {idx + 1}  ·  Matriks Jacobian tidak tersedia.")
			return

		raw_rows = len(jacobian)
		raw_cols = len(jacobian[0]) if raw_rows > 0 else 0

		if raw_rows % 3 == 0 and raw_rows == raw_cols and raw_rows > 0:
			n_cells = raw_rows // 3
			size = raw_rows
			reordered: list[list[float]] = [[0.0] * size for _ in range(size)]
			for new_r in range(size):
				old_r = (new_r % 3) * n_cells + (new_r // 3)
				for new_c in range(size):
					old_c = (new_c % 3) * n_cells + (new_c // 3)
					reordered[new_r][new_c] = jacobian[old_r][old_c]
			display_data = reordered
		else:
			n_cells = 0
			display_data = jacobian

		well_cell = self.project_config.wells[0].cell_id if self.project_config and self.project_config.wells else None
		self._jacobian_canvas.set_data(display_data, n_cells, 1.0, well_cell=well_cell)
		self._apply_jacobian_zoom()

		n = len(display_data)
		max_abs = max((abs(v) for row in display_data for v in row), default=0.0)
		self._jacobian_status.setText(
			f"Step {idx + 1}  ·  {n}×{n}  ·  {n_cells} sel  ·  Max |J|: {max_abs:.4e}"
		)

	def _extract_pressure_jacobian(self, step: TimeStepResult) -> list[list[float]]:
		jacobian = getattr(step, "jacobian", [])
		if not jacobian:
			return []
		raw_rows = len(jacobian)
		raw_cols = len(jacobian[0]) if raw_rows > 0 else 0
		if raw_rows <= 0 or raw_rows != raw_cols or raw_rows % 3 != 0:
			return []
		n_cells = raw_rows // 3
		return [list(row[:n_cells]) for row in jacobian[:n_cells]]

	def _extract_cell_diag_jacobian(self, step: TimeStepResult | None) -> dict[str, list[float]]:
		jacobian = getattr(step, "jacobian", []) if step is not None else []
		if not jacobian:
			return {}
		raw_rows = len(jacobian)
		raw_cols = len(jacobian[0]) if raw_rows > 0 else 0
		if raw_rows <= 0 or raw_rows != raw_cols or raw_rows % 3 != 0:
			return {}
		n_cells = raw_rows // 3
		diag: dict[str, list[float]] = {key: [] for key, _, _, _ in _JAC_DIAG_COMPONENTS}
		for cell_idx in range(n_cells):
			for key, _, row_block, col_block in _JAC_DIAG_COMPONENTS:
				row = row_block * n_cells + cell_idx
				col = col_block * n_cells + cell_idx
				diag[key].append(float(jacobian[row][col]))
		return diag

	def _jacobian_sym_heat(self, value: float, max_abs: float) -> tuple[QColor, QColor]:
		if max_abs <= 1e-30 or abs(value) < 1e-30:
			return QColor("#F7F9FB"), QColor("#5B6676")
		t = min(math.sqrt(abs(value) / max_abs), 1.0)
		def _blend(a: tuple[int, int, int], b: tuple[int, int, int], f: float) -> QColor:
			return QColor(
				int(a[0] + f * (b[0] - a[0])),
				int(a[1] + f * (b[1] - a[1])),
				int(a[2] + f * (b[2] - a[2])),
			)
		if value > 0:
			bg = _blend((219, 234, 254), (30, 58, 138), t)
		else:
			bg = _blend((254, 226, 226), (136, 19, 55), t)
		fg = QColor("#1F2937") if t < 0.45 else QColor("#F7F9FB")
		return bg, fg

	def _rebuild_jacobian_sym_grid(self) -> None:
		if not hasattr(self, "_jac_sym_grid_layout"):
			return
		while self._jac_sym_grid_layout.count():
			item = self._jac_sym_grid_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
		self._jac_sym_btns.clear()
		self._jac_sym_selected_cell = None
		for row in range(self._ny):
			for col in range(self._nx):
				n = row * self._nx + col + 1
				btn = QPushButton()
				btn.setObjectName("symGridCell")
				btn.setProperty("mode", "normal")
				btn.setFixedSize(72, 62)
				btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
				btn.setCursor(Qt.CursorShape.PointingHandCursor)
				btn.clicked.connect(lambda _=False, cell=n: self._select_jacobian_sym_cell(cell))
				self._jac_sym_btns[n] = btn
				self._jac_sym_grid_layout.addWidget(btn, row, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
		total = max(self._nx * self._ny, 1)
		if hasattr(self, "_jac_sym_well_spin"):
			self._jac_sym_well_spin.setRange(1, total)
			self._jac_sym_well_spin.setValue(min(self._well_cell, total))
		self._refresh_jacobian_sym_grid()

	def _refresh_jacobian_sym_grid(self) -> None:
		step = None
		jpp: list[list[float]] = []
		diag: dict[str, list[float]] = {}
		if self._run_result is not None and self._run_result.steps and hasattr(self, "_jac_sym_step_combo"):
			idx = self._jac_sym_step_combo.currentIndex()
			if 0 <= idx < len(self._run_result.steps):
				step = self._run_result.steps[idx]
				jpp = self._extract_pressure_jacobian(step)
				diag = self._extract_cell_diag_jacobian(step)
		sym_set = set(_symmetric_cells(self._jac_sym_selected_cell, self._well_cell, self._nx, self._ny)) if self._jac_sym_selected_cell is not None else set()

		for n, btn in self._jac_sym_btns.items():
			is_well = n == self._well_cell
			is_sel = n == self._jac_sym_selected_cell
			is_sym = n in sym_set
			mode = "well" if is_well else ("selected" if is_sel else ("symmetric" if is_sym else "normal"))
			text = str(n)
			if diag.get("p") and n <= len(diag["p"]):
				value = diag["p"][n - 1]
				text = f"{n}\nP {value:.1e}"
			elif jpp and n <= len(jpp):
				value = jpp[n - 1][n - 1]
				text = f"{n}\nP {value:.1e}"
			if is_well and not is_sel:
				text += "\nWELL"
			elif is_sym:
				text += "\nSIM"
			btn.setStyleSheet("")
			btn.setProperty("mode", mode)
			_repolish(btn)
			btn.setText(text)

	def _select_jacobian_sym_cell(self, n: int) -> None:
		self._jac_sym_selected_cell = n
		self._refresh_jacobian_sym_grid()
		self._update_jacobian_sym_cards()

	def _on_jacobian_sym_well_changed(self, value: int) -> None:
		self._well_cell = value
		self._refresh_jacobian_sym_grid()
		self._update_jacobian_sym_cards()

	def _populate_jacobian_symmetry(self) -> None:
		if not hasattr(self, "_jac_sym_step_combo"):
			return
		if self._run_result is None or not self._run_result.steps:
			self._jac_sym_status.setText("Jalankan simulasi dulu.")
			self._refresh_jacobian_sym_grid()
			self._update_jacobian_sym_cards()
			return
		idx = self._jac_sym_step_combo.currentIndex()
		if idx < 0 or idx >= len(self._run_result.steps):
			return
		step = self._run_result.steps[idx]
		jpp = self._extract_pressure_jacobian(step)
		diag = self._extract_cell_diag_jacobian(step)
		if not jpp or not diag:
			self._jac_sym_status.setText(f"Step {idx + 1}  ·  Blok Jacobian 3x3 tidak tersedia.")
		else:
			max_abs = max((abs(v) for row in jpp for v in row), default=0.0)
			max_diag = max((abs(v) for vals in diag.values() for v in vals), default=0.0)
			self._jac_sym_status.setText(
				f"Step {idx + 1}  ·  Jpp {len(jpp)}×{len(jpp)}  ·  diag p/Sw/Sg  ·  "
				f"Max |Jpp|: {max_abs:.4e}  ·  Max |diag|: {max_diag:.4e}"
			)
		self._refresh_jacobian_sym_grid()
		self._update_jacobian_sym_cards()

	def _update_jacobian_sym_cards(self) -> None:
		if not hasattr(self, "_jac_sym_body"):
			return
		n = self._jac_sym_selected_cell
		_clear_layout(self._jac_sym_body)
		if n is None:
			msg = QLabel("Pilih sel untuk membandingkan simetri pressure row dan diag cell p/Sw/Sg.")
			msg.setObjectName("resultRowLabel")
			msg.setWordWrap(True)
			self._jac_sym_body.addWidget(msg)
			self._jac_sym_sel_title.setText("DIAG CELL JACOBIAN: —")
			for lbl in (self._jac_sym_diag, self._jac_sym_diag_sw, self._jac_sym_diag_sg, self._jac_sym_well, self._jac_sym_rowmax):
				lbl.setText("—")
			return
		step = None
		if self._run_result is not None and self._run_result.steps:
			idx = self._jac_sym_step_combo.currentIndex()
			if 0 <= idx < len(self._run_result.steps):
				step = self._run_result.steps[idx]
		jpp = self._extract_pressure_jacobian(step) if step is not None else []
		diag = self._extract_cell_diag_jacobian(step)
		self._jac_sym_sel_title.setText(f"DIAG CELL JACOBIAN: SEL {n}")
		if not jpp or not diag or n > len(jpp) or n > len(diag.get("p", [])):
			for lbl in (self._jac_sym_diag, self._jac_sym_diag_sw, self._jac_sym_diag_sg, self._jac_sym_well, self._jac_sym_rowmax):
				lbl.setText("—")
			msg = QLabel("Data Jacobian 3x3 belum tersedia untuk step ini.")
			msg.setObjectName("resultRowLabel")
			msg.setWordWrap(True)
			self._jac_sym_body.addWidget(msg)
			return
		self._jac_sym_diag.setText(f"{diag['p'][n - 1]:.4e}  (Ro-p)")
		self._jac_sym_diag_sw.setText(f"{diag['sw'][n - 1]:.4e}  (Rw-Sw)")
		self._jac_sym_diag_sg.setText(f"{diag['sg'][n - 1]:.4e}  (Rg-Sg)")
		self._jac_sym_well.setText(f"{diag['p'][self._well_cell - 1]:.4e}" if self._well_cell <= len(diag['p']) else "—")
		self._jac_sym_rowmax.setText(f"{max((abs(v) for vals in diag.values() for v in vals), default=0.0):.4e}")

		syms = _symmetric_cells(n, self._well_cell, self._nx, self._ny)
		if not syms:
			msg = QLabel("Tidak ada pasangan simetris untuk sel ini.")
			msg.setObjectName("resultRowLabel")
			msg.setWordWrap(True)
			self._jac_sym_body.addWidget(msg)
			return

		for s in syms:
			code = _symmetry_transform_code_for_pair(n, s, self._well_cell, self._nx, self._ny)
			if code is None or s > len(jpp) or s > len(diag["p"]):
				continue
			diffs: list[float] = []
			denoms: list[float] = []
			compared_cells: list[tuple[int, int]] = []
			for c in range(1, len(jpp) + 1):
				mapped = _apply_symmetry_transform(c, self._well_cell, self._nx, self._ny, code)
				if mapped is None or mapped > len(jpp):
					continue
				v1 = jpp[n - 1][c - 1]
				v2 = jpp[s - 1][mapped - 1]
				diffs.append(abs(v1 - v2))
				denoms.append(max(abs(v1), abs(v2), 1e-30))
				compared_cells.append((c, mapped))
			compared = len(compared_cells)
			max_rel = max((d / denom for d, denom in zip(diffs, denoms)), default=0.0)
			mean_abs = sum(diffs) / compared if compared else 0.0
			diag_rel: dict[str, float] = {}
			for key, _, _, _ in _JAC_DIAG_COMPONENTS:
				v1 = diag[key][n - 1]
				v2 = diag[key][s - 1]
				d = abs(v1 - v2)
				diag_rel[key] = d / max(abs(v1), abs(v2), 1e-30)
			max_diag_rel = max(diag_rel.values(), default=0.0)
			pass_check = max(max_rel, max_diag_rel) < 1e-4

			chip = QFrame()
			chip.setObjectName("symCheckChip")
			chip.setProperty("state", "pass" if pass_check else "fail")
			_repolish(chip)
			chip_lay = QVBoxLayout(chip)
			chip_lay.setContentsMargins(8, 6, 8, 6)
			chip_lay.setSpacing(2)
			lbl = QLabel(f"{'PASS' if pass_check else 'FAIL'}  Sel {n} ↔ Sel {s}")
			lbl.setObjectName("symCheckLabel")
			chip_lay.addWidget(lbl)
			detail = QLabel(
				f"Pressure row: {compared} elemen  ·  max rel diff: {max_rel:.3e}  ·  mean abs diff: {mean_abs:.3e}\n"
				f"Diag cell: p {diag['p'][n - 1]:.3e} ↔ {diag['p'][s - 1]:.3e} (rel {diag_rel['p']:.3e})  ·  "
				f"Sw {diag['sw'][n - 1]:.3e} ↔ {diag['sw'][s - 1]:.3e} (rel {diag_rel['sw']:.3e})  ·  "
				f"Sg {diag['sg'][n - 1]:.3e} ↔ {diag['sg'][s - 1]:.3e} (rel {diag_rel['sg']:.3e})"
			)
			detail.setObjectName("resultRowLabel")
			detail.setWordWrap(True)
			chip_lay.addWidget(detail)
			self._jac_sym_body.addWidget(chip)

	def _get_jacobian_cell_color(self, val: float, max_abs: float) -> tuple[QColor, QColor]:
		"""
		Light-background diverging palette matching the header blue theme.
		  Zero     → soft tint  (#DCEAF7)  muted text
		  Positive → blue-100  → blue-500 → blue-900
		  Negative → rose-100  → rose-500 → rose-900
		  Text     → petroleum-blue (#0F5C8E) on light cells, white on dark cells
		"""
		import math

		if max_abs <= 0.0 or abs(val) < 1e-30:
			return QColor("#DCEAF7"), QColor("#93A1B2")

		t = math.sqrt(abs(val) / max_abs)

		def _L(a: int, b: int, f: float) -> int:
			return max(0, min(255, int(a + f * (b - a))))

		def _s3(c0, c1, c2, f):
			if f <= 0.5:
				s = f * 2.0
				return _L(c0[0],c1[0],s), _L(c0[1],c1[1],s), _L(c0[2],c1[2],s)
			s = (f - 0.5) * 2.0
			return _L(c1[0],c2[0],s), _L(c1[1],c2[1],s), _L(c1[2],c2[2],s)

		if val > 0:
			# blue-100 (#dbeafe) → blue-500 (#3b82f6) → blue-900 (#1e3a8a)
			r, g, b = _s3((0xdb,0xea,0xfe), (0x3b,0x82,0xf6), (0x1e,0x3a,0x8a), t)
		else:
			# rose-100 (#ffe4e6) → rose-500 (#f43f5e) → rose-900 (#881337)
			r, g, b = _s3((0xff,0xe4,0xe6), (0xf4,0x3f,0x5e), (0x88,0x13,0x37), t)

		bg = QColor(r, g, b)
		brightness = 0.299 * r + 0.587 * g + 0.114 * b
		fg = QColor("#0F5C8E") if brightness > 180 else QColor("#F7F9FB")
		return bg, fg

	def _refresh_jacobian_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._jacobian_status.setText("Jalankan simulasi dulu.")
			self.jacobian_step_combo.blockSignals(True)
			self.jacobian_step_combo.clear()
			self.jacobian_step_combo.blockSignals(False)
			self._jacobian_canvas.set_data([], 0)
			return

		current_idx = self.jacobian_step_combo.currentIndex()
		self.jacobian_step_combo.blockSignals(True)
		self.jacobian_step_combo.clear()
		for si, s in enumerate(self._run_result.steps, 1):
			self.jacobian_step_combo.addItem(
				f"Step {si}  ·  t = {s.summary.time_days:.2f} d"
			)
		new_idx = len(self._run_result.steps) - 1
		if 0 <= current_idx < len(self._run_result.steps):
			new_idx = current_idx
		self.jacobian_step_combo.setCurrentIndex(new_idx)
		self.jacobian_step_combo.blockSignals(False)

		self._populate_jacobian_display()
		self._refresh_jacobian_symmetry_tab()

	def _refresh_jacobian_symmetry_tab(self) -> None:
		if not hasattr(self, "_jac_sym_step_combo"):
			return
		if self._run_result is None or not self._run_result.steps:
			self._jac_sym_status.setText("Jalankan simulasi dulu.")
			self._jac_sym_step_combo.blockSignals(True)
			self._jac_sym_step_combo.clear()
			self._jac_sym_step_combo.blockSignals(False)
			self._refresh_jacobian_sym_grid()
			self._update_jacobian_sym_cards()
			return
		current_idx = self._jac_sym_step_combo.currentIndex()
		self._jac_sym_step_combo.blockSignals(True)
		self._jac_sym_step_combo.clear()
		for si, s in enumerate(self._run_result.steps, 1):
			self._jac_sym_step_combo.addItem(f"Step {si}  ·  t = {s.summary.time_days:.2f} d")
		new_idx = len(self._run_result.steps) - 1
		if 0 <= current_idx < len(self._run_result.steps):
			new_idx = current_idx
		self._jac_sym_step_combo.setCurrentIndex(new_idx)
		self._jac_sym_step_combo.blockSignals(False)
		self._populate_jacobian_symmetry()

	def _jacobian_zoom_in(self) -> None:
		self._set_jacobian_autofit(False)
		if self._jacobian_zoom_idx < len(_JACOBIAN_ZOOM_STEPS) - 1:
			self._jacobian_zoom_idx += 1
			self._apply_jacobian_zoom()

	def _jacobian_zoom_out(self) -> None:
		self._set_jacobian_autofit(False)
		if self._jacobian_zoom_idx > 0:
			self._jacobian_zoom_idx -= 1
			self._apply_jacobian_zoom()

	def _jacobian_zoom_reset(self) -> None:
		self._jacobian_zoom_idx = _JACOBIAN_ZOOM_DEFAULT_IDX
		self._set_jacobian_autofit(True)
		self._apply_jacobian_zoom()

	def _on_jacobian_fit_toggled(self, checked: bool) -> None:
		self._set_jacobian_autofit(checked)
		self._apply_jacobian_zoom()

	def _set_jacobian_autofit(self, enabled: bool) -> None:
		self._jacobian_autofit = enabled
		self.btn_jacobian_fit.setChecked(enabled)

	def _on_jacobian_viewport_resized(self) -> None:
		if not self._jacobian_autofit:
			return
		if not hasattr(self, "_jacobian_resize_timer"):
			self._jacobian_resize_timer = QTimer(self)
			self._jacobian_resize_timer.setSingleShot(True)
			self._jacobian_resize_timer.timeout.connect(self._apply_jacobian_zoom)
		self._jacobian_resize_timer.start(30)

	def _compute_jacobian_fit_zoom(self) -> float:
		natural  = self._jacobian_canvas.natural_size()
		viewport = self._jacobian_scroll.viewport().size()
		avail_w  = max(1, viewport.width()  - 4)
		avail_h  = max(1, viewport.height() - 4)
		zoom = min(avail_w / natural.width(), avail_h / natural.height())
		return max(0.05, min(zoom, 8.0))

	def _apply_jacobian_zoom(self) -> None:
		if self._jacobian_autofit:
			z = self._compute_jacobian_fit_zoom()
		else:
			z = _JACOBIAN_ZOOM_STEPS[self._jacobian_zoom_idx]
		self._jacobian_zoom_label.setText(f"{int(z * 100)}%")
		self._jacobian_canvas.set_zoom(z)

	# =========================================================================
	# Newton Corrections tab
	# =========================================================================

	def _build_corrections_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultCorrectionsTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(14, 12, 14, 14)
		vlay.setSpacing(10)

		# Toolbar row
		toolbar = QWidget()
		toolbar.setObjectName("resultToolbar")
		tbar_lay = QHBoxLayout(toolbar)
		tbar_lay.setContentsMargins(12, 8, 12, 8)
		tbar_lay.setSpacing(10)

		self._corrections_status = QLabel("Jalankan simulasi dulu.")
		self._corrections_status.setObjectName("resultStatusLine")
		self._corrections_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		tbar_lay.addWidget(self._corrections_status, 1)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(step_lbl)

		self.corrections_step_combo = QComboBox()
		self.corrections_step_combo.setObjectName("resultCorrectionsStepCombo")
		self.corrections_step_combo.setMinimumWidth(140)
		self.corrections_step_combo.currentIndexChanged.connect(self._on_corrections_step_changed)
		tbar_lay.addWidget(self.corrections_step_combo)

		iter_lbl = QLabel("Newton Iterasi:")
		iter_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(iter_lbl)

		self.corrections_iter_combo = QComboBox()
		self.corrections_iter_combo.setObjectName("resultCorrectionsIterCombo")
		self.corrections_iter_combo.setMinimumWidth(110)
		self.corrections_iter_combo.currentIndexChanged.connect(self._on_corrections_iter_changed)
		tbar_lay.addWidget(self.corrections_iter_combo)

		vlay.addWidget(toolbar)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		splitter.setHandleWidth(6)
		splitter.setChildrenCollapsible(False)

		# Left Card: Numerical values table
		table_card = QFrame()
		table_card.setObjectName("resultCard")
		tc_lay = QVBoxLayout(table_card)
		tc_lay.setContentsMargins(12, 10, 12, 10)
		tc_lay.setSpacing(6)

		tc_title = QLabel("NILAI KOREKSI PER CELL")
		tc_title.setObjectName("resultCardTitle")
		tc_lay.addLayout(_title_row(tc_title, "K", "#A86A15"))

		self.corrections_table = QTableWidget()
		self.corrections_table.setObjectName("dataTable")
		self.corrections_table.setColumnCount(4)
		self.corrections_table.setHorizontalHeaderLabels(["Cell", "δp (psia)", "δSw (frac)", "δSg (frac)"])
		self.corrections_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.corrections_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.corrections_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.corrections_table.verticalHeader().setVisible(False)
		self.corrections_table.setAlternatingRowColors(True)

		th = self.corrections_table.horizontalHeader()
		th.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		th.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
		self.corrections_table.setColumnWidth(0, 62)

		tc_lay.addWidget(self.corrections_table, 1)
		splitter.addWidget(table_card)

		# Right Card: Chart
		chart_card = QFrame()
		chart_card.setObjectName("resultCard")
		cc_lay = QVBoxLayout(chart_card)
		cc_lay.setContentsMargins(12, 10, 12, 10)
		cc_lay.setSpacing(6)

		cc_title = QLabel("GRAFIK KOREKSI NEWTON")
		cc_title.setObjectName("resultCardTitle")
		cc_lay.addLayout(_title_row(cc_title, "G", "#B2413F"))

		self.corrections_chart = _CorrectionChartWidget()
		cc_lay.addWidget(self.corrections_chart, 1)
		splitter.addWidget(chart_card)

		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 1)
		splitter.setSizes([450, 650])

		vlay.addWidget(splitter, 1)
		return w

	def _on_corrections_step_changed(self) -> None:
		self._update_corrections_iter_combo()

	def _on_corrections_iter_changed(self) -> None:
		self._populate_corrections_display()

	def _update_corrections_iter_combo(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self.corrections_iter_combo.blockSignals(True)
			self.corrections_iter_combo.clear()
			self.corrections_iter_combo.blockSignals(False)
			return

		step_idx = self.corrections_step_combo.currentIndex()
		if step_idx < 0 or step_idx >= len(self._run_result.steps):
			return
		step = self._run_result.steps[step_idx]

		corrections = getattr(step, "corrections", [])

		self.corrections_iter_combo.blockSignals(True)
		self.corrections_iter_combo.clear()
		if corrections:
			for i in range(len(corrections)):
				self.corrections_iter_combo.addItem(f"Iterasi {i + 1}")
			self.corrections_iter_combo.setCurrentIndex(len(corrections) - 1)
		self.corrections_iter_combo.blockSignals(False)

		self._populate_corrections_display()

	def _populate_corrections_display(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self.corrections_table.setRowCount(0)
			self.corrections_chart.set_data([], [], [])
			return

		step_idx = self.corrections_step_combo.currentIndex()
		if step_idx < 0 or step_idx >= len(self._run_result.steps):
			return
		step = self._run_result.steps[step_idx]

		corrections = getattr(step, "corrections", [])
		iter_idx = self.corrections_iter_combo.currentIndex()

		if not corrections or iter_idx < 0 or iter_idx >= len(corrections):
			self.corrections_table.setRowCount(0)
			self.corrections_chart.set_data([], [], [])
			self._corrections_status.setText(f"Step {step_idx + 1}  ·  Tidak ada data koreksi.")
			return

		corr_vec = corrections[iter_idx]
		n_total = len(corr_vec)

		if n_total % 3 == 0 and n_total > 0:
			n_cells = n_total // 3
			dp = corr_vec[0 : n_cells]
			dsw = corr_vec[n_cells : 2 * n_cells]
			dsg = corr_vec[2 * n_cells : 3 * n_cells]
		else:
			n_cells = n_total
			dp = corr_vec
			dsw = [0.0] * n_cells
			dsg = [0.0] * n_cells

		self.corrections_table.setRowCount(n_cells)
		for i in range(n_cells):
			v_dp = dp[i] if i < len(dp) else 0.0
			v_dsw = dsw[i] if i < len(dsw) else 0.0
			v_dsg = dsg[i] if i < len(dsg) else 0.0

			item_cell = QTableWidgetItem(f"Sel {i + 1}")
			item_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.corrections_table.setItem(i, 0, item_cell)

			item_dp = QTableWidgetItem(f"{v_dp:.6e}")
			item_dp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			if abs(v_dp) > 1e-12:
				item_dp.setForeground(QBrush(QColor("#0F5C8E")))
			self.corrections_table.setItem(i, 1, item_dp)

			item_dsw = QTableWidgetItem(f"{v_dsw:.6e}")
			item_dsw.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			if abs(v_dsw) > 1e-12:
				item_dsw.setForeground(QBrush(QColor("#2563A6")))
			self.corrections_table.setItem(i, 2, item_dsw)

			item_dsg = QTableWidgetItem(f"{v_dsg:.6e}")
			item_dsg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			if abs(v_dsg) > 1e-12:
				item_dsg.setForeground(QBrush(QColor("#0F766E")))
			self.corrections_table.setItem(i, 3, item_dsg)

		self.corrections_chart.set_data(dp, dsw, dsg)

		self._corrections_status.setText(
			f"Step {step_idx + 1}  ·  Iterasi {iter_idx + 1} dari {len(corrections)}  ·  "
			f"Max |δp|: {max((abs(v) for v in dp), default=0.0):.4e}  ·  "
			f"Max |δSw|: {max((abs(v) for v in dsw), default=0.0):.4e}  ·  "
			f"Max |δSg|: {max((abs(v) for v in dsg), default=0.0):.4e}"
		)

	def _refresh_corrections_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._corrections_status.setText("Jalankan simulasi dulu.")
			self.corrections_step_combo.blockSignals(True)
			self.corrections_step_combo.clear()
			self.corrections_step_combo.blockSignals(False)
			self.corrections_iter_combo.blockSignals(True)
			self.corrections_iter_combo.clear()
			self.corrections_iter_combo.blockSignals(False)
			self.corrections_table.setRowCount(0)
			self.corrections_chart.set_data([], [], [])
			return

		current_idx = self.corrections_step_combo.currentIndex()
		self.corrections_step_combo.blockSignals(True)
		self.corrections_step_combo.clear()
		for si, s in enumerate(self._run_result.steps, 1):
			self.corrections_step_combo.addItem(
				f"Step {si}  ·  t = {s.summary.time_days:.2f} d"
			)
		new_idx = len(self._run_result.steps) - 1
		if 0 <= current_idx < len(self._run_result.steps):
			new_idx = current_idx
		self.corrections_step_combo.setCurrentIndex(new_idx)
		self.corrections_step_combo.blockSignals(False)

		self._update_corrections_iter_combo()

	def _build_summary_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultSummaryTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(14, 14, 14, 14)
		vlay.setSpacing(10)

		self.summary_label = QLabel("Jalankan simulasi untuk melihat validasi model.")
		self.summary_label.setObjectName("resultStatusLine")
		self.summary_label.setWordWrap(True)
		vlay.addWidget(self.summary_label)

		stats_grid = QGridLayout()
		stats_grid.setContentsMargins(0, 0, 0, 0)
		stats_grid.setHorizontalSpacing(10)
		stats_grid.setVerticalSpacing(10)

		card_steps, self._sum_steps = _make_stat_card("Steps", icon="#", color="#0F5C8E")
		card_time, self._sum_time = _make_stat_card("Final Time", icon="T", color="#2563A6")
		card_conv, self._sum_converged = _make_stat_card("Converged", icon="✓", color="#2D6A4F")
		card_maxr, self._sum_maxr = _make_stat_card("Max Residual", icon="R", color="#B2413F")
		card_att, self._sum_attempts = _make_stat_card("Attempts", icon="A", color="#08395A")
		card_rej, self._sum_rejected = _make_stat_card("Rejected", icon="X", color="#B2413F")

		stats_grid.addWidget(card_steps, 0, 0)
		stats_grid.addWidget(card_time, 0, 1)
		stats_grid.addWidget(card_conv, 0, 2)
		stats_grid.addWidget(card_maxr, 1, 0)
		stats_grid.addWidget(card_att, 1, 1)
		stats_grid.addWidget(card_rej, 1, 2)
		vlay.addLayout(stats_grid)

		phase_card, _ = _make_card("Residual Per Fase", icon="R", color="#A86A15")
		self._sum_oil = _add_row(phase_card, "Oil", "-")
		self._sum_water = _add_row(phase_card, "Water", "-")
		self._sum_gas = _add_row(phase_card, "Gas", "-")
		vlay.addWidget(phase_card)

		self.warning_label = QLabel("")
		self.warning_label.setObjectName("resultWarningText")
		self.warning_label.setWordWrap(True)
		self.warning_label.setVisible(False)
		vlay.addWidget(self.warning_label)
		vlay.addStretch(1)
		return w

	def _build_retry_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultRetryTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(16, 12, 16, 16)
		vlay.setSpacing(8)
		self.retry_scope_combo  = QComboBox()
		self.retry_status_combo = QComboBox()
		self.retry_scope_combo.addItems(["Latest Step Only", "All Steps"])
		self.retry_status_combo.addItems(["All Attempts", "Rejected Only", "Accepted Only"])
		self.retry_stats_label = QLabel("Retry table: 0 row(s)")
		self.retry_stats_label.setObjectName("resultStatusLine")

		toolbar = QWidget()
		toolbar.setObjectName("resultToolbar")
		tbar_lay = QHBoxLayout(toolbar)
		tbar_lay.setContentsMargins(12, 8, 12, 8)
		tbar_lay.setSpacing(10)
		scope_lbl = QLabel("Scope:")
		scope_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(scope_lbl)
		tbar_lay.addWidget(self.retry_scope_combo)
		status_lbl = QLabel("Status:")
		status_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(status_lbl)
		tbar_lay.addWidget(self.retry_status_combo)
		tbar_lay.addStretch(1)
		tbar_lay.addWidget(self.retry_stats_label)
		vlay.addWidget(toolbar)

		self.retry_table = QTableWidget(0, 7)
		self.retry_table.setObjectName("dataTable")
		self.retry_table.setHorizontalHeaderLabels(
			["Step", "Retry", "Target Time (days)", "dt (days)",
			 "Max Residual", "Residual Norm", "Status"]
		)
		self.retry_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.retry_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
		self.retry_table.setSortingEnabled(True)
		self.retry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.retry_table.verticalHeader().setVisible(False)
		self.retry_table.setAlternatingRowColors(True)
		vlay.addWidget(self.retry_table)
		return w

	def _build_comparison_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultComparisonTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(16, 14, 16, 16)
		vlay.setSpacing(14)

		hint = QLabel(
			"Tiap kali Run diklik, hasilnya mengisi kartu sesuai method yang aktif di "
			"halaman Methods. Jalankan sekali per method untuk melihat perbandingan."
		)
		hint.setObjectName("resultStatusLine")
		hint.setWordWrap(True)
		vlay.addWidget(hint)

		cards_row = QHBoxLayout()
		cards_row.setSpacing(12)
		self._comparison_newton_card = _ComparisonCard("Newton-Raphson")
		self._comparison_quasi_card = _ComparisonCard("Quasi-Newton")
		cards_row.addWidget(self._comparison_newton_card, 1)
		cards_row.addWidget(self._comparison_quasi_card, 1)
		vlay.addLayout(cards_row)

		self._comparison_delta_label = QLabel("")
		self._comparison_delta_label.setObjectName("resultStatusLine")
		self._comparison_delta_label.setWordWrap(True)
		vlay.addWidget(self._comparison_delta_label)

		diagram_card, _ = _make_card("Konsep Newton-Raphson 1D (ilustratif)", icon="N", color="#0F5C8E")
		diagram_note = QLabel(
			"Diagram generik untuk intuisi — bukan diplot dari hasil run di atas. x mewakili "
			"satu unknown (p, Sw, atau Sg), r(x) mewakili residual mass-balance."
		)
		diagram_note.setObjectName("resultRowLabel")
		diagram_note.setWordWrap(True)
		diagram_card.layout().addWidget(diagram_note)
		self._newton_concept_diagram = _NewtonConceptDiagram()
		diagram_card.layout().addWidget(self._newton_concept_diagram)
		vlay.addWidget(diagram_card, 1)

		return w

	def set_comparison_results(
		self,
		newton_result: RunResult | None,
		quasi_result: RunResult | None,
	) -> None:
		self._comparison_newton_card.set_result(newton_result)
		self._comparison_quasi_card.set_result(quasi_result)
		if newton_result is None or quasi_result is None:
			self._comparison_delta_label.setText("")
			return
		newton_iters = sum(step.summary.newton_iterations for step in newton_result.steps)
		quasi_iters = sum(step.summary.newton_iterations for step in quasi_result.steps)
		newton_elapsed = newton_result.total_elapsed_seconds
		quasi_elapsed = quasi_result.total_elapsed_seconds
		iter_delta = quasi_iters - newton_iters
		speedup = (newton_elapsed / quasi_elapsed) if quasi_elapsed > 1e-9 else 0.0
		self._comparison_delta_label.setText(
			f"Selisih iterasi (Quasi-Newton vs Newton-Raphson): {iter_delta:+d}  ·  "
			f"CPU time: {newton_elapsed:.3f}s vs {quasi_elapsed:.3f}s  ·  "
			f"speedup {speedup:.2f}x"
		)

	# =========================================================================
	# Grid widget
	# =========================================================================

	def _rebuild_grid(self) -> None:
		if not hasattr(self, "_grid_layout"):
			return
		while self._grid_layout.count():
			item = self._grid_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
		self._cell_btns.clear()
		self._selected_cell = None

		for row in range(self._ny):
			for col in range(self._nx):
				n = row * self._nx + col + 1
				btn = QPushButton()
				btn.setObjectName("symGridCell")
				btn.setProperty("mode", "normal")
				btn.setFixedSize(92, 78)
				btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
				btn.setCursor(Qt.CursorShape.PointingHandCursor)
				btn.clicked.connect(lambda _=False, cell=n: self._select_cell(cell))
				self._cell_btns[n] = btn
				self._grid_layout.addWidget(btn, row, col, Qt.AlignmentFlag.AlignCenter)

		self._update_grid_hint()
		self._refresh_cell_colors()

	def _refresh_cell_colors(self) -> None:
		if not self._cell_btns:
			return
		connected = {cell for cell, _ in self._get_selected_grid_connections(self._selected_cell)}
		step = self._latest_step()
		for n, btn in self._cell_btns.items():
			if n == self._selected_cell:
				mode = "selected"
			elif n in connected:
				mode = "symmetric"
			else:
				mode = "normal"

			label = str(n)
			if step and step.pressure and n <= len(step.pressure):
				label += f"\n{step.pressure[n - 1]:.0f}"
			if n in connected:
				label += "\nCONN"

			btn.setProperty("mode", mode)
			_repolish(btn)
			btn.setText(label)

	def _select_cell(self, n: int) -> None:
		self._selected_cell = n
		self._refresh_cell_colors()
		self._update_sel_card()
		self._update_sym_card()

	def _update_sel_card(self) -> None:
		n = self._selected_cell
		if n is None:
			return
		row, col = divmod(n - 1, self._nx)
		connections = self._get_selected_grid_connections(n)
		self._sel_card_title.setText(f"SELECTED CELL: {n}  (row {row + 1}, col {col + 1})")

		step = self._latest_step()
		if step and step.pressure and n <= len(step.pressure):
			idx = n - 1
			self._lbl_sel_p.setText(f"{step.pressure[idx]:.2f} psia")
			self._lbl_sel_sw.setText(f"{step.sw[idx]:.4f}")
			self._lbl_sel_sg.setText(f"{step.sg[idx]:.4f}")
		else:
			for lbl in (self._lbl_sel_p, self._lbl_sel_sw, self._lbl_sel_sg):
				lbl.setText("—")
		self._lbl_sel_res.setText(f"{len(connections)} cell")

	def _get_selected_grid_connections(self, n: int | None) -> list[tuple[int, object]]:
		if n is None or self.project_config is None:
			return []
		try:
			grid_model = build_grid(self.project_config)
			update_grid_transmissibility(grid_model)
		except Exception:
			return []
		selected_0 = n - 1
		connections: list[tuple[int, object]] = []
		for conn in grid_model.connections:
			if conn.from_cell_id == selected_0:
				connections.append((conn.to_cell_id + 1, conn))
			elif conn.to_cell_id == selected_0:
				connections.append((conn.from_cell_id + 1, conn))
		return sorted(connections, key=lambda item: item[0])

	def _update_sym_card(self) -> None:
		n = self._selected_cell
		_clear_layout(self._sym_body)
		connections = self._get_selected_grid_connections(n)
		if n is None:
			h = QLabel("Pilih cell untuk melihat koneksi langsung.")
			h.setObjectName("resultRowLabel")
			h.setWordWrap(True)
			self._sym_body.addWidget(h)
			return
		if not connections:
			h = QLabel(f"Cell {n} tidak punya koneksi aktif pada grid model.")
			h.setObjectName("resultRowLabel")
			h.setWordWrap(True)
			self._sym_body.addWidget(h)
			return
		for neighbor, _conn in connections:
			chip = QFrame()
			chip.setObjectName("symCheckChip")
			chip.setProperty("state", "pass")
			_repolish(chip)
			chip_lay = QHBoxLayout(chip)
			chip_lay.setContentsMargins(8, 5, 8, 5)
			chip_lbl = QLabel(f"Cell {n} ↔ Cell {neighbor}")
			chip_lbl.setObjectName("symCheckLabel")
			chip_lay.addWidget(chip_lbl, 1)
			self._sym_body.addWidget(chip)

	def _on_well_changed(self, value: int) -> None:
		self._well_cell = value
		self._refresh_cell_colors()
		if self._selected_cell is not None:
			self._update_sym_card()

	# =========================================================================
	# Residual tab
	# =========================================================================

	def _on_resid_step_changed(self) -> None:
		self._populate_resid_table()

	def _populate_resid_table(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._resid_table.setRowCount(0)
			return
		idx = self._resid_step_combo.currentIndex()
		if idx < 0 or idx >= len(self._run_result.steps):
			return
		step = self._run_result.steps[idx]

		oil   = step.oil_residual_per_cell   or []
		water = step.water_residual_per_cell or []
		gas   = step.gas_residual_per_cell   or []
		n_cells = max(len(oil), len(water), len(gas))

		# Per-phase global maxima for color scaling
		max_oil   = max((abs(v) for v in oil),   default=1e-30)
		max_water = max((abs(v) for v in water), default=1e-30)
		max_gas   = max((abs(v) for v in gas),   default=1e-30)

		def _blend(c1: tuple[int, int, int], c2: tuple[int, int, int], f: float) -> QColor:
			return QColor(
				int(c1[0] + f * (c2[0] - c1[0])),
				int(c1[1] + f * (c2[1] - c1[1])),
				int(c1[2] + f * (c2[2] - c1[2])),
			)

		def _heat(value: float, scale: float) -> tuple[QColor, QColor]:
			"""Sign-aware diverging scale: blue = positive, red = negative, grey ≈ 0."""
			mag = abs(value) / max(scale, 1e-30)
			t = min(math.sqrt(mag), 1.0)
			if t < 1e-6:
				return QColor("#F1F4F8"), QColor("#93A1B2")
			if value > 0:
				bg = _blend((219, 234, 254), (29, 78, 216), t)   # blue-100 → blue-700
			else:
				bg = _blend((254, 226, 226), (185, 28, 28), t)   # red-100 → red-700
			fg = QColor("#1F2937") if t < 0.55 else QColor("#ffffff")
			return bg, fg

		mono_font = QFont("Consolas", 9)
		self._resid_table.setRowCount(n_cells)
		for i in range(n_cells):
			v_oil   = oil[i]   if i < len(oil)   else 0.0
			v_water = water[i] if i < len(water) else 0.0
			v_gas   = gas[i]   if i < len(gas)   else 0.0

			cell_item = QTableWidgetItem(f"Sel {i + 1}")
			cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			cell_item.setFont(QFont("Segoe UI Variable Text", 9, QFont.Weight.Bold))
			self._resid_table.setItem(i, 0, cell_item)

			for col, val, mx in [(1, v_oil, max_oil), (2, v_water, max_water), (3, v_gas, max_gas)]:
				it = QTableWidgetItem(f"{val:+.4e}")
				it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				it.setFont(mono_font)
				bg, fg = _heat(val, mx)
				it.setBackground(bg)
				it.setForeground(fg)
				self._resid_table.setItem(i, col, it)

	def _refresh_residual_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._resid_status.setText("Jalankan simulasi dulu.")
			self._resid_conv_badge.setText("—")
			self._resid_conv_badge.setProperty("status", "empty")
			_repolish(self._resid_conv_badge)
			for lbl in self._resid_phase_lbls.values():
				lbl.setText("—")
			self._resid_step_combo.blockSignals(True)
			self._resid_step_combo.clear()
			self._resid_step_combo.blockSignals(False)
			self._resid_table.setRowCount(0)
			return

		# Rebuild step combo preserving selection
		current_idx = self._resid_step_combo.currentIndex()
		self._resid_step_combo.blockSignals(True)
		self._resid_step_combo.clear()
		for si, s in enumerate(self._run_result.steps, 1):
			self._resid_step_combo.addItem(
				f"Step {si}  ·  t = {s.summary.time_days:.2f} d"
			)
		new_idx = len(self._run_result.steps) - 1  # default to last step
		if 0 <= current_idx < len(self._run_result.steps):
			new_idx = current_idx
		self._resid_step_combo.setCurrentIndex(new_idx)
		self._resid_step_combo.blockSignals(False)

		step = self._run_result.steps[new_idx]
		converged = step.summary.converged
		n_cells = max(
			len(step.oil_residual_per_cell or []),
			len(step.water_residual_per_cell or []),
			len(step.gas_residual_per_cell or []),
		)
		self._resid_status.setText(
			f"Step {new_idx + 1}  ·  t = {step.summary.time_days:.2f} hari  ·  {n_cells} sel"
		)
		self._resid_conv_badge.setText("✓ Konvergen" if converged else "✗ Belum Konvergen")
		self._resid_conv_badge.setProperty("status", "ok" if converged else "fail")
		_repolish(self._resid_conv_badge)
		self._resid_phase_lbls["oil"].setText(f"{step.max_oil_residual:.4e}")
		self._resid_phase_lbls["water"].setText(f"{step.max_water_residual:.4e}")
		self._resid_phase_lbls["gas"].setText(f"{step.max_gas_residual:.4e}")
		self._populate_resid_table()

	# =========================================================================
	# Convergence tab
	# =========================================================================

	def _refresh_conv_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._conv_status.setText("Jalankan simulasi dulu.")
			self._conv_table.setRowCount(0)
			self._conv_chart.set_data([])
			return

		steps = self._run_result.steps
		n_ok = sum(1 for s in steps if s.summary.converged)
		self._conv_status.setText(
			f"{len(steps)} step total  ·  {n_ok} konvergen  ·  {len(steps) - n_ok} gagal"
		)

		# Flatten all attempts into table rows
		rows: list[tuple[int, float, float, int, float, float, bool]] = []
		for si, step in enumerate(steps, 1):
			if step.attempts:
				for att in step.attempts:
					rows.append((
						si,
						step.summary.time_days,
						att.dt_days,
						step.summary.newton_iterations,
						att.max_residual,
						att.residual_norm,
						att.converged,
					))
			else:
				rows.append((
					si,
					step.summary.time_days,
					0.0,
					step.summary.newton_iterations,
					step.summary.max_residual,
					0.0,
					step.summary.converged,
				))

		_COLOR_GREEN_BG = QColor("#DCEEE3")
		_COLOR_RED_BG   = QColor("#F6DEDC")
		_COLOR_GREEN_FG = QColor("#1F4D38")
		_COLOR_RED_FG   = QColor("#7A2B29")
		_COLOR_HEADER   = QColor("#5B6676")

		self._conv_table.setRowCount(len(rows))
		for r, (si, t, dt, iters, maxr, norm, ok) in enumerate(rows):
			bg = _COLOR_GREEN_BG if ok else _COLOR_RED_BG
			fg = _COLOR_GREEN_FG if ok else _COLOR_RED_FG
			values = [
				str(si),
				f"{t:.2f}",
				f"{dt:.3f}",
				str(iters),
				f"{maxr:.3e}",
				f"{norm:.3e}",
				"✓  konvergen" if ok else "✗  gagal",
			]
			for c, val in enumerate(values):
				item = QTableWidgetItem(val)
				item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				item.setBackground(bg)
				item.setForeground(fg)
				self._conv_table.setItem(r, c, item)

		# Build norm series for chart: one point per step (last attempt)
		norm_series: list[tuple[int, float, bool]] = []
		for si, step in enumerate(steps, 1):
			if step.attempts:
				att = step.attempts[-1]
				norm_series.append((si, att.residual_norm, att.converged))
			else:
				norm_series.append((si, step.summary.max_residual, step.summary.converged))
		self._conv_chart.set_data(norm_series)

	# =========================================================================
	# Retry log helpers (preserved logic)
	# =========================================================================

	def _build_retry_rows(self, run_result: RunResult) -> list[tuple]:
		rows: list[tuple] = []
		step_indices = range(1, len(run_result.steps) + 1)
		if self.retry_scope_combo.currentText() == "Latest Step Only" and run_result.steps:
			step_indices = [len(run_result.steps)]
		for step_index in step_indices:
			step = run_result.steps[step_index - 1]
			for attempt in step.attempts:
				if self.retry_status_combo.currentText() == "Rejected Only" and attempt.converged:
					continue
				if self.retry_status_combo.currentText() == "Accepted Only" and not attempt.converged:
					continue
				rows.append((
					step_index, attempt.retry_index,
					attempt.target_time_days, attempt.dt_days,
					attempt.max_residual, attempt.residual_norm,
					attempt.note,
				))
		return rows

	def _refresh_retry_table(self) -> None:
		run_result = self._active_run_result
		if run_result is None:
			self.retry_table.setRowCount(0)
			self.retry_stats_label.setText("Retry table: 0 row(s)")
			return
		rows = self._build_retry_rows(run_result)
		self.retry_table.setSortingEnabled(False)
		self.retry_table.setRowCount(len(rows))
		for ri, row_data in enumerate(rows):
			for ci, value in enumerate(row_data):
				cell_text = f"{value:.6f}" if isinstance(value, float) else str(value)
				item = QTableWidgetItem(cell_text)
				if ci == 6:
					sv = str(value)
					if sv == "accepted":
						item.setBackground(QColor("#1F4D38"))
					elif sv == "abort-min-dt":
						item.setBackground(QColor("#7A2B29"))
					else:
						item.setBackground(QColor("#6B4710"))
				self.retry_table.setItem(ri, ci, item)
		self.retry_table.setSortingEnabled(True)
		self.retry_table.sortByColumn(
			0, self.retry_table.horizontalHeader().sortIndicatorOrder()
		)
		self.retry_stats_label.setText(f"Retry table: {len(rows)} row(s)")

	# =========================================================================
	# Helpers
	# =========================================================================

	def _latest_step(self) -> TimeStepResult | None:
		if self._run_result and self._run_result.steps:
			return self._run_result.steps[-1]
		return None

	def _update_grid_hint(self) -> None:
		cells_xy = self._nx * self._ny
		self._grid_hint.setText(
			f"Grid {self._nx} x {self._ny} ({cells_xy} sel XY)  ·  klik cell untuk melihat koneksi langsung."
		)

	# =========================================================================
	# Public API
	# =========================================================================

	def show_group(self, index: int) -> None:
		"""Select which top-level group is visible — driven by the Validation
		section buttons in the main window sidebar, not an in-page tab bar."""
		self._tabs.setCurrentIndex(index)

	def set_project(self, project_config: ProjectConfig) -> None:
		"""Update grid dimensions from project. Rebuilds grid if size changed."""
		self.project_config = project_config
		self._grid_connection_3d_page.set_project(project_config)
		gs = project_config.grid_spec
		changed = (gs.nx != self._nx or gs.ny != self._ny)
		self._nx = gs.nx
		self._ny = gs.ny
		if project_config.wells:
			# Symmetry is checked relative to the well actually placed in Well Placement.
			self._well_cell = project_config.wells[0].cell_id
		else:
			# No well placed yet — fall back to grid centre as a neutral default.
			cx = max(gs.nx // 2, 0)
			cy = max(gs.ny // 2, 0)
			self._well_cell = cy * gs.nx + cx + 1
		if changed:
			self._rebuild_grid()
			self._rebuild_jacobian_sym_grid()
		else:
			self._update_grid_hint()
			if hasattr(self, "_jac_sym_well_spin"):
				self._jac_sym_well_spin.blockSignals(True)
				self._jac_sym_well_spin.setRange(1, max(gs.nx * gs.ny, 1))
				self._jac_sym_well_spin.setValue(self._well_cell)
				self._jac_sym_well_spin.blockSignals(False)
			self._refresh_jacobian_sym_grid()

	def set_run_result(self, run_result: RunResult | None) -> None:
		self._run_result = run_result
		self._active_run_result = run_result
		self._grid_connection_3d_page.set_run_result(run_result)
		self._refresh_jacobian_symmetry_tab()

		if run_result is None:
			self.summary_label.setText("Jalankan simulasi untuk melihat validasi model.")
			self._sum_steps.setText("-")
			self._sum_time.setText("-")
			self._sum_converged.setText("-")
			self._sum_maxr.setText("-")
			self._sum_attempts.setText("-")
			self._sum_rejected.setText("-")
			self._sum_oil.setText("-")
			self._sum_water.setText("-")
			self._sum_gas.setText("-")
			self.warning_label.setText("")
			self.warning_label.setVisible(False)
			self.retry_table.setRowCount(0)
			self.retry_stats_label.setText("Retry table: 0 row(s)")
			self._resid_status.setText("Jalankan simulasi dulu.")
			self._prop_status.setText("Jalankan simulasi dulu.")
			self.prop_table.setRowCount(0)
			self._clear_prop_grid()
			self._refresh_multistep_tab()
			self._badge.setText("")
			self._badge.setProperty("status", "empty")
			self._badge.hide()
			_repolish(self._badge)
			self._refresh_jacobian_tab()
			self._refresh_corrections_tab()
			return

		step_count = len(run_result.steps)
		warn_count = len(run_result.warnings)
		self._badge.setText(f"{step_count} step(s)  •  {warn_count} warning(s)")
		self._badge.setProperty("status", "ok" if not warn_count else "warn")
		self._badge.hide()
		_repolish(self._badge)

		s = get_run_summary(run_result)
		self.summary_label.setText("Ringkasan run terakhir")
		self._sum_steps.setText(str(s["step_count"]))
		self._sum_time.setText(f"{s['final_time_days']} days")
		self._sum_converged.setText("Yes" if s["last_converged"] else "No")
		self._sum_maxr.setText(str(s["last_max_residual"]))
		self._sum_attempts.setText(str(s["retry_attempt_count"]))
		self._sum_rejected.setText(str(s["rejected_attempt_count"]))
		self._sum_oil.setText(str(s["last_max_oil_residual"]))
		self._sum_water.setText(str(s["last_max_water_residual"]))
		self._sum_gas.setText(str(s["last_max_gas_residual"]))

		if run_result.warnings:
			self.warning_label.setText("Warnings:\n• " + "\n• ".join(run_result.warnings))
			self.warning_label.setVisible(True)
		else:
			self.warning_label.setText("")
			self.warning_label.setVisible(False)

		self._refresh_retry_table()
		self._refresh_residual_tab()
		self._refresh_conv_tab()
		self._refresh_jacobian_tab()
		self._refresh_corrections_tab()
		self._refresh_properties_tab()
		self._refresh_multistep_tab()
		self._refresh_cell_colors()
		if self._selected_cell is not None:
			self._update_sel_card()
			self._update_sym_card()

	# =========================================================================
	# Property Maps tab
	# =========================================================================

	def _build_properties_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultPropertiesTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(14, 12, 14, 14)
		vlay.setSpacing(10)

		# Toolbar
		toolbar = QWidget()
		toolbar.setObjectName("resultToolbar")
		tbar_lay = QHBoxLayout(toolbar)
		tbar_lay.setContentsMargins(12, 8, 12, 8)
		tbar_lay.setSpacing(10)

		self._prop_status = QLabel("Jalankan simulasi dulu.")
		self._prop_status.setObjectName("resultStatusLine")
		self._prop_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		tbar_lay.addWidget(self._prop_status, 1)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(step_lbl)

		self.prop_step_combo = QComboBox()
		self.prop_step_combo.setObjectName("resultPropStepCombo")
		self.prop_step_combo.setMinimumWidth(140)
		self.prop_step_combo.currentIndexChanged.connect(self._on_prop_step_changed)
		tbar_lay.addWidget(self.prop_step_combo)

		# "Properti" only matters for the Heatmap sub-tab (Table already
		# shows every property at once) — its combo lives there instead of
		# this shared bar, see the Heatmap tab section below.
		self.prop_select_combo = QComboBox()
		self.prop_select_combo.setObjectName("resultPropSelectCombo")
		self.prop_select_combo.setMinimumWidth(210)

		# Properties list matching Step 7 visual matrix
		self._properties_meta = [
			("pressure_psia", "p (psia) - Tekanan", "plasma"),
			("so", "So - Saturasi Oil", "YlOrRd"),
			("sw", "Sw - Saturasi Water", "Blues"),
			("sg", "Sg - Saturasi Gas", "Greens"),
			("bo", "Bo (rb/stb) - FVF Oil", "autumn"),
			("bw", "Bw (rb/stb) - FVF Water", "winter"),
			("bg", "Bg (rcf/scf) - FVF Gas", "copper"),
			("mu_o", "mu_o (cp) - Viskositas Oil", "hot"),
			("mu_w", "mu_w (cp) - Viskositas Water", "cool"),
			("mu_g", "mu_g (cp) - Viskositas Gas", "viridis"),
			("kro", "kro - Relperm Oil", "YlOrRd"),
			("krw", "krw - Relperm Water", "Blues"),
			("krg", "krg - Relperm Gas", "Greens"),
			("lam_o", "lam_o (1/cp) - Mobilitas Oil", "plasma"),
			("lam_w", "lam_w (1/cp) - Mobilitas Water", "plasma"),
			("lam_g", "lam_g (1/cp) - Mobilitas Gas", "plasma"),
			("rho_o", "rho_o (lbm/ft3) - Densitas Oil", "hot"),
			("rho_w", "rho_w (lbm/ft3) - Densitas Water", "cool"),
			("rho_g", "rho_g (lbm/ft3) - Densitas Gas", "viridis"),
			("pcow", "Pcow (psi) - Tekanan Kapilari Oil-Water", "YlOrRd"),
			("pcgw", "Pcgw (psi) - Tekanan Kapilari Gas-Water", "Greens"),
		]
		for prop_key, prop_title, prop_cmap in self._properties_meta:
			self.prop_select_combo.addItem(prop_title, (prop_key, prop_cmap))

		self.prop_select_combo.currentIndexChanged.connect(self._on_prop_type_changed)

		vlay.addWidget(toolbar)

		self._prop_content_tabs = QTabWidget()
		self._prop_content_tabs.setObjectName("subTabs")
		self._prop_content_tabs.tabBar().setObjectName("subTabBar")
		self._prop_content_tabs.tabBar().setExpanding(False)
		self._prop_content_tabs.setDocumentMode(True)

		# Table tab
		table_card = QFrame()
		table_card.setObjectName("resultCard")
		tc_lay = QVBoxLayout(table_card)
		tc_lay.setContentsMargins(12, 10, 12, 10)
		tc_lay.setSpacing(6)

		tc_title = QLabel("TABEL SEMUA PROPERTI PER CELL")
		tc_title.setObjectName("resultCardTitle")
		tc_lay.addLayout(_title_row(tc_title, "P", "#0F5C8E"))

		table_ctrl = QHBoxLayout()
		table_ctrl.setContentsMargins(0, 0, 0, 0)
		table_ctrl.setSpacing(8)
		self._prop_table_view_combo = QComboBox()
		self._prop_table_view_combo.setObjectName("pageCompactControl")
		self._prop_table_view_combo.setMinimumWidth(130)
		self._prop_table_view_combo.addItem("Scroll", "scroll")
		self._prop_table_view_combo.addItem("Fit", "fit")
		self._prop_table_view_combo.setToolTip("Mode tampilan tabel")
		table_ctrl.addWidget(self._prop_table_view_combo)
		self._prop_table_filter = QLineEdit()
		self._prop_table_filter.setObjectName("pageCompactField")
		self._prop_table_filter.setPlaceholderText("Search table")
		table_ctrl.addWidget(self._prop_table_filter, 1)
		self._prop_table_meta = QLabel("0 rows")
		self._prop_table_meta.setObjectName("resultToolbarLabel")
		table_ctrl.addWidget(self._prop_table_meta)
		tc_lay.addLayout(table_ctrl)

		self.prop_table = QTableWidget()
		self.prop_table.setObjectName("dataTable")
		self.prop_table.setToolTip("Klik header kolom untuk sort")
		self._prop_table_headers = [
			"Cell", "i", "j", "p (psia)", "So", "Sw", "Sg", "Bo", "Bw", "Bg",
			"mu_o", "mu_w", "mu_g", "kro", "krw", "krg", "lam_o", "lam_w", "lam_g",
			"rho_o", "rho_w", "rho_g", "Pcow", "Pcgw"
		]
		self._prop_table_headers_compact = [
			"Cell", "i", "j", "p", "So", "Sw", "Sg", "Bo", "Bw", "Bg",
			"mu_o", "mu_w", "mu_g", "kro", "krw", "krg", "lam_o", "lam_w", "lam_g",
			"rho_o", "rho_w", "rho_g", "Pcow", "Pcgw"
		]
		self._prop_table_column_keys = [
			"cell", "i_index", "j_index", "pressure_psia", "so", "sw", "sg", "bo", "bw", "bg",
			"mu_o", "mu_w", "mu_g", "kro", "krw", "krg", "lam_o", "lam_w", "lam_g",
			"rho_o", "rho_w", "rho_g", "pcow", "pcgw"
		]
		self.prop_table.setColumnCount(len(self._prop_table_headers))
		self.prop_table.setHorizontalHeaderLabels(self._prop_table_headers)
		self.prop_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.prop_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.prop_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.prop_table.verticalHeader().setVisible(False)
		self.prop_table.setShowGrid(False)
		self.prop_table.setAlternatingRowColors(True)
		self.prop_table.setWordWrap(False)
		self.prop_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		self.prop_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		self.prop_table.setCornerButtonEnabled(False)
		self.prop_table.setSortingEnabled(True)

		ph = self.prop_table.horizontalHeader()
		ph.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		ph.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
		ph.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
		for col_idx in range(3, len(self._prop_table_headers)):
			ph.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Fixed)
			self.prop_table.setColumnWidth(col_idx, 96)
		self._prop_table_view_combo.currentIndexChanged.connect(self._populate_properties_display)
		self._prop_table_filter.textChanged.connect(self._populate_properties_display)
		tc_lay.addWidget(self.prop_table, 1)
		self._prop_content_tabs.addTab(table_card, "  Table  ")

		# Heatmap tab
		map_card = QFrame()
		map_card.setObjectName("resultCard")
		mc_lay = QVBoxLayout(map_card)
		mc_lay.setContentsMargins(12, 10, 12, 10)
		mc_lay.setSpacing(6)

		self.map_title = QLabel("PETA GRID HEATMAP: p (psia)")
		self.map_title.setObjectName("resultCardTitle")

		map_title_row = _title_row(self.map_title, "M", "#2D6A4F")
		prop_lbl = QLabel("Properti:")
		prop_lbl.setObjectName("resultToolbarLabel")
		map_title_row.addWidget(prop_lbl)
		map_title_row.addWidget(self.prop_select_combo)
		cmap_lbl = QLabel("Warna:")
		cmap_lbl.setObjectName("resultToolbarLabel")
		map_title_row.addWidget(cmap_lbl)
		self.heatmap_cmap_combo = QComboBox()
		self.heatmap_cmap_combo.setObjectName("pageCompactControl")
		self.heatmap_cmap_combo.setMinimumWidth(190)
		self.heatmap_cmap_combo.setToolTip("Pilih skema warna heatmap")
		for cmap_label, cmap_key in COLORMAP_CHOICES:
			self.heatmap_cmap_combo.addItem(cmap_label, cmap_key)
		self.heatmap_cmap_combo.currentIndexChanged.connect(self._populate_properties_display)
		map_title_row.addWidget(self.heatmap_cmap_combo)
		mc_lay.addLayout(map_title_row)

		self.prop_grid_scroll = QScrollArea()
		self.prop_grid_scroll.setObjectName("resultGridScroll")
		self.prop_grid_scroll.setWidgetResizable(True)
		self.prop_grid_scroll.setFrameShape(QFrame.Shape.NoFrame)

		self.prop_grid_container = QWidget()
		self.prop_grid_container.setObjectName("resultGridPanel")
		self.prop_grid_layout = QGridLayout(self.prop_grid_container)
		self.prop_grid_layout.setSpacing(8)
		self.prop_grid_layout.setContentsMargins(12, 12, 12, 12)
		self.prop_grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.prop_grid_scroll.setWidget(self.prop_grid_container)

		map_content_row = QHBoxLayout()
		map_content_row.setContentsMargins(0, 0, 0, 0)
		map_content_row.setSpacing(6)
		map_content_row.addWidget(self.prop_grid_scroll, 1)
		self.colorbar_widget = _ColorbarWidget(self, orientation=Qt.Orientation.Vertical)
		map_content_row.addWidget(self.colorbar_widget)
		mc_lay.addLayout(map_content_row, 1)
		self._prop_content_tabs.addTab(map_card, "  Heatmap  ")

		self._prop_content_tabs.addTab(self._build_multistep_tab(), "  Per Waktu  ")

		vlay.addWidget(self._prop_content_tabs, 1)
		return w

	def _clear_grid_layout(self, layout: QGridLayout, widgets: dict[int, "_HeatmapCellWidget"]) -> None:
		while layout.count():
			item = layout.takeAt(0)
			w = item.widget()
			if w is not None:
				# Detach immediately rather than relying solely on deleteLater()
				# — until the deferred delete actually runs, a widget that's
				# merely taken out of the layout stays a visible child at its
				# last geometry, which can show up as a stray duplicate tile.
				w.hide()
				w.setParent(None)
				w.deleteLater()
		widgets.clear()

	def _clear_prop_grid(self) -> None:
		self._clear_grid_layout(self.prop_grid_layout, self._prop_cell_widgets)

	def _populate_heatmap_grid(
		self,
		cell_props_list: list[dict],
		grid_layout: QGridLayout,
		widgets: dict[int, "_HeatmapCellWidget"],
		prop_key: str,
		cmap: str,
		colorbar: "_ColorbarWidget",
		label: str,
		cell_size: tuple[int, int] | None = None,
		value_range: tuple[float, float] | None = None,
	) -> None:
		"""Fill a grid layout with colored cells for one property/step.

		Shared by the single Heatmap tab and each panel of the Per Waktu
		tab so both views render identically. `value_range`, when given,
		fixes vmin/vmax instead of rescaling to this step's own min/max --
		used by the Per Waktu tab so color actually evolves across the
		timestep scrubber instead of every frame re-stretching its own
		(often near-constant) local spread to the full colormap.
		"""
		self._clear_grid_layout(grid_layout, widgets)

		if value_range is not None:
			vmin, vmax = value_range
		else:
			prop_vals = [cell_data[prop_key] for cell_data in cell_props_list]
			vmin = min(prop_vals)
			vmax = max(prop_vals)
		colorbar.set_scale(vmin, vmax, cmap, label)
		fmt_str = PROP_VALUE_FORMATS.get(prop_key, "{:.4f}")

		n_cells = len(cell_props_list)
		if cell_size is not None:
			cell_w, cell_h = cell_size
		else:
			cell_w = 120 if n_cells <= 16 else (80 if n_cells <= 100 else 55)
			cell_h = 100 if n_cells <= 16 else (70 if n_cells <= 100 else 50)

		for cell_data in cell_props_list:
			cell_no = cell_data["cell"]
			i_val = cell_data["i_index"]
			j_val = cell_data["j_index"]
			val = cell_data[prop_key]

			bg_color, fg_color = get_color_from_colormap(val, vmin, vmax, cmap)

			cell_widget = _HeatmapCellWidget(cell_no)
			cell_widget.update_cell(val, bg_color, fg_color, fmt_str, cell_w, cell_h)

			widgets[cell_no] = cell_widget
			grid_layout.addWidget(cell_widget, j_val, i_val)

	def _refresh_properties_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._prop_status.setText("Jalankan simulasi dulu.")
			self.prop_step_combo.blockSignals(True)
			self.prop_step_combo.clear()
			self.prop_step_combo.blockSignals(False)
			self.prop_table.setRowCount(0)
			self._prop_table_meta.setText("0 rows")
			self._clear_prop_grid()
			return

		# Sync step selection
		current_idx = self.prop_step_combo.currentIndex()
		self.prop_step_combo.blockSignals(True)
		self.prop_step_combo.clear()
		for si, s in enumerate(self._run_result.steps, 1):
			self.prop_step_combo.addItem(
				f"Step {si}  ·  t = {s.summary.time_days:.2f} d"
			)
		new_idx = len(self._run_result.steps) - 1
		if 0 <= current_idx < len(self._run_result.steps):
			new_idx = current_idx
		self.prop_step_combo.setCurrentIndex(new_idx)
		self.prop_step_combo.blockSignals(False)

		step = self._run_result.steps[new_idx]
		n_cells = len(step.pressure)
		self._prop_status.setText(
			f"Step {new_idx + 1}  ·  Grid {self._nx}x{self._ny} ({n_cells} sel)  ·  t = {step.summary.time_days:.2f} d"
		)

		self._populate_properties_display()

	def _on_prop_step_changed(self) -> None:
		self._populate_properties_display()

	def _on_prop_type_changed(self) -> None:
		self._populate_properties_display()

	def _apply_prop_table_column_mode(self) -> None:
		head = self.prop_table.horizontalHeader()
		mode = self._prop_table_view_combo.currentData() if hasattr(self, "_prop_table_view_combo") else "scroll"
		if mode == "fit":
			self.prop_table.setHorizontalHeaderLabels(self._prop_table_headers_compact)
			head.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
			head.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
			head.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
			self.prop_table.setColumnWidth(0, 62)
			self.prop_table.setColumnWidth(1, 38)
			self.prop_table.setColumnWidth(2, 38)
			for col_idx in range(3, len(self._prop_table_headers)):
				head.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Fixed)
				self.prop_table.setColumnWidth(col_idx, 72)
		else:
			self.prop_table.setHorizontalHeaderLabels(self._prop_table_headers)
			head.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
			head.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
			head.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
			for col_idx in range(3, len(self._prop_table_headers)):
				head.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Fixed)
				self.prop_table.setColumnWidth(col_idx, 96)

	def _populate_properties_display(self) -> None:
		if self._run_result is None or not self._run_result.steps or self.project_config is None:
			return

		step_idx = self.prop_step_combo.currentIndex()
		if step_idx < 0 or step_idx >= len(self._run_result.steps):
			return

		step = self._run_result.steps[step_idx]
		cell_props_list = get_all_cell_properties(self.project_config, step)

		# 1. Populate Table
		self._apply_prop_table_column_mode()

		fmts = PROP_VALUE_FORMATS

		filter_text = self._prop_table_filter.text().strip().lower() if hasattr(self, "_prop_table_filter") else ""

		filtered_rows = []
		for cell_data in cell_props_list:
			search_blob = " ".join(
				str(cell_data.get(key, "")) for key in self._prop_table_column_keys
			).lower()
			if filter_text and filter_text not in search_blob:
				continue
			filtered_rows.append(cell_data)

		self.prop_table.setRowCount(len(filtered_rows))
		self._prop_table_meta.setText(f"{len(filtered_rows)} / {len(cell_props_list)} rows")
		sort_section = self.prop_table.horizontalHeader().sortIndicatorSection()
		sort_order = self.prop_table.horizontalHeader().sortIndicatorOrder()
		row_height = 30 if (self._prop_table_view_combo.currentData() == "fit") else 34
		self.prop_table.setSortingEnabled(False)

		for r, cell_data in enumerate(filtered_rows):
			cell_no = cell_data["cell"]
			i_val = cell_data["i_index"]
			j_val = cell_data["j_index"]

			item_cell = _SortableTableItem(f"Sel {cell_no}", cell_no)
			item_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.prop_table.setItem(r, 0, item_cell)

			item_i = _SortableTableItem(str(i_val), i_val)
			item_i.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.prop_table.setItem(r, 1, item_i)

			item_j = _SortableTableItem(str(j_val), j_val)
			item_j.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.prop_table.setItem(r, 2, item_j)

			for col_idx, col_header in enumerate(self._prop_table_headers[3:], start=3):
				prop_key = self._properties_meta[col_idx - 3][0]
				val = cell_data[prop_key]
				fmt = fmts.get(prop_key, "{:.4f}")

				item = _SortableTableItem(fmt.format(val), float(val))
				item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				item.setForeground(QBrush(QColor("#5B6676")))
				self.prop_table.setItem(r, col_idx, item)
			self.prop_table.setRowHeight(r, row_height)

		self.prop_table.setSortingEnabled(True)
		if sort_section >= 0:
			self.prop_table.sortItems(sort_section, sort_order)

		# 2. Populate Heatmap Grid
		selected_prop_idx = self.prop_select_combo.currentIndex()
		if selected_prop_idx < 0:
			self._clear_prop_grid()
			return

		prop_key, default_cmap = self.prop_select_combo.currentData()
		prop_label = self.prop_select_combo.currentText()
		override_cmap = self.heatmap_cmap_combo.currentData()
		prop_cmap = override_cmap or default_cmap

		self.map_title.setText(f"PETA GRID HEATMAP: {prop_label}")
		self._populate_heatmap_grid(
			cell_props_list, self.prop_grid_layout, self._prop_cell_widgets,
			prop_key, prop_cmap, self.colorbar_widget, prop_label,
		)

	# =========================================================================
	# Per Waktu (time-lapse comparison) tab
	# =========================================================================

	def _build_multistep_panel(self, default_prop_idx: int) -> tuple[QFrame, "_MultiStepPanel"]:
		"""Build one property card used inside the Per Waktu side-by-side row."""
		card = QFrame()
		card.setObjectName("resultCard")
		lay = QVBoxLayout(card)
		lay.setContentsMargins(10, 8, 10, 8)
		lay.setSpacing(6)

		combo = QComboBox()
		combo.setObjectName("pageCompactControl")
		for prop_key, prop_title, prop_cmap in self._properties_meta:
			combo.addItem(prop_title, (prop_key, prop_cmap))
		combo.setCurrentIndex(default_prop_idx)
		lay.addWidget(combo)

		title_label = QLabel(combo.currentText())
		title_label.setObjectName("resultCardTitle")
		lay.addLayout(_title_row(title_label, "M", "#2D6A4F"))

		scroll = QScrollArea()
		scroll.setObjectName("resultGridScroll")
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)

		container = QWidget()
		container.setObjectName("resultGridPanel")
		grid_layout = QGridLayout(container)
		grid_layout.setSpacing(4)
		grid_layout.setContentsMargins(8, 8, 8, 8)
		grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
		scroll.setWidget(container)

		content_row = QHBoxLayout()
		content_row.setContentsMargins(0, 0, 0, 0)
		content_row.setSpacing(6)
		content_row.addWidget(scroll, 1)
		colorbar = _ColorbarWidget(card, orientation=Qt.Orientation.Vertical)
		content_row.addWidget(colorbar)
		lay.addLayout(content_row, 1)

		panel = _MultiStepPanel(combo=combo, grid_layout=grid_layout, colorbar=colorbar, title_label=title_label)
		combo.currentIndexChanged.connect(self._on_multistep_panel_combo_changed)
		return card, panel

	def _build_multistep_tab(self) -> QWidget:
		"""3 side-by-side property heatmaps with a shared timestep scrubber —
		lets the user compare e.g. Pressure / Sw / Sg evolving step by step.
		"""
		card = QFrame()
		card.setObjectName("resultCard")
		vlay = QVBoxLayout(card)
		vlay.setContentsMargins(12, 10, 12, 10)
		vlay.setSpacing(8)

		header = QLabel("PERBANDINGAN ANTAR TIMESTEP")
		header.setObjectName("resultCardTitle")
		vlay.addLayout(_title_row(header, "T", "#0F5C8E"))

		playback = QHBoxLayout()
		playback.setContentsMargins(0, 0, 0, 0)
		playback.setSpacing(8)

		self.cmp_prev_btn = QPushButton("‹")
		self.cmp_prev_btn.setObjectName("resultToolbarBtn")
		self.cmp_prev_btn.setFixedWidth(32)
		self.cmp_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
		self.cmp_prev_btn.setToolTip("Step sebelumnya")
		self.cmp_prev_btn.clicked.connect(lambda: self._multistep_step_to("prev"))
		playback.addWidget(self.cmp_prev_btn)

		self.cmp_play_btn = QPushButton("▶")
		self.cmp_play_btn.setObjectName("resultToolbarBtn")
		self.cmp_play_btn.setFixedWidth(32)
		self.cmp_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
		self.cmp_play_btn.setToolTip("Putar otomatis per timestep")
		self.cmp_play_btn.clicked.connect(self._multistep_play_toggle)
		playback.addWidget(self.cmp_play_btn)

		self.cmp_next_btn = QPushButton("›")
		self.cmp_next_btn.setObjectName("resultToolbarBtn")
		self.cmp_next_btn.setFixedWidth(32)
		self.cmp_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
		self.cmp_next_btn.setToolTip("Step berikutnya")
		self.cmp_next_btn.clicked.connect(lambda: self._multistep_step_to("next"))
		playback.addWidget(self.cmp_next_btn)

		self.cmp_step_slider = QSlider(Qt.Orientation.Horizontal)
		self.cmp_step_slider.setObjectName("resultStepSlider")
		self.cmp_step_slider.setRange(0, 0)
		self.cmp_step_slider.valueChanged.connect(self._on_multistep_slider_changed)
		playback.addWidget(self.cmp_step_slider, 1)

		self.cmp_step_label = QLabel("Jalankan simulasi dulu.")
		self.cmp_step_label.setObjectName("resultToolbarLabel")
		self.cmp_step_label.setMinimumWidth(170)
		playback.addWidget(self.cmp_step_label)

		vlay.addLayout(playback)

		panels_row = QHBoxLayout()
		panels_row.setContentsMargins(0, 0, 0, 0)
		panels_row.setSpacing(10)

		self._multistep_panels = []
		default_indices = [0, 2, 3]  # pressure_psia, sw, sg in self._properties_meta
		for default_idx in default_indices:
			panel_card, panel = self._build_multistep_panel(default_idx)
			panels_row.addWidget(panel_card, 1)
			self._multistep_panels.append(panel)

		vlay.addLayout(panels_row, 1)
		return card

	def _refresh_multistep_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._multistep_stop_playback()
			self.cmp_step_slider.blockSignals(True)
			self.cmp_step_slider.setRange(0, 0)
			self.cmp_step_slider.setValue(0)
			self.cmp_step_slider.blockSignals(False)
			self.cmp_step_slider.setEnabled(False)
			self.cmp_play_btn.setEnabled(False)
			self.cmp_prev_btn.setEnabled(False)
			self.cmp_next_btn.setEnabled(False)
			self.cmp_step_label.setText("Jalankan simulasi dulu.")
			for panel in self._multistep_panels:
				self._clear_grid_layout(panel.grid_layout, panel.cell_widgets)
			self._multistep_global_ranges = {}
			return

		n_steps = len(self._run_result.steps)
		has_multiple = n_steps > 1
		self.cmp_step_slider.setEnabled(has_multiple)
		self.cmp_play_btn.setEnabled(has_multiple)
		self.cmp_prev_btn.setEnabled(has_multiple)
		self.cmp_next_btn.setEnabled(has_multiple)

		current = self.cmp_step_slider.value()
		new_idx = current if 0 <= current < n_steps else n_steps - 1
		self.cmp_step_slider.blockSignals(True)
		self.cmp_step_slider.setRange(0, n_steps - 1)
		self.cmp_step_slider.setValue(new_idx)
		self.cmp_step_slider.blockSignals(False)

		self._multistep_global_ranges = self._compute_multistep_global_ranges()
		self._populate_multistep_panels(new_idx)

	def _compute_multistep_global_ranges(self) -> dict[str, tuple[float, float]]:
		"""Fixed vmin/vmax per property across ALL saved timesteps.

		Computed once (when the run result changes) rather than per slider
		tick, and used as a fixed color scale for the Per Waktu tab so
		scrubbing through time shows a real color trend instead of every
		frame independently re-stretching its own narrow value spread to
		the full colormap (which made small, near-constant differences look
		like one extreme outlier cell next to a flat sea of gray).
		"""
		ranges: dict[str, tuple[float, float]] = {}
		if self._run_result is None or self.project_config is None:
			return ranges
		prop_keys = [key for key, _, _ in self._properties_meta]
		for step in self._run_result.steps:
			cell_props_list = get_all_cell_properties(self.project_config, step)
			for prop_key in prop_keys:
				vals = [c[prop_key] for c in cell_props_list]
				lo, hi = min(vals), max(vals)
				prev = ranges.get(prop_key)
				ranges[prop_key] = (min(prev[0], lo), max(prev[1], hi)) if prev else (lo, hi)
		return ranges

	def _populate_multistep_panels(self, step_idx: int) -> None:
		if self._run_result is None or self.project_config is None or not self._run_result.steps:
			return
		step_idx = max(0, min(step_idx, len(self._run_result.steps) - 1))
		step = self._run_result.steps[step_idx]
		self.cmp_step_label.setText(
			f"Step {step_idx + 1}/{len(self._run_result.steps)}  ·  t = {step.summary.time_days:.2f} d"
		)

		cell_props_list = get_all_cell_properties(self.project_config, step)
		n_cells = len(cell_props_list)
		cell_size = (70, 56) if n_cells <= 16 else ((48, 40) if n_cells <= 100 else (30, 26))

		for panel in self._multistep_panels:
			prop_key, cmap = panel.combo.currentData()
			label = panel.combo.currentText()
			panel.title_label.setText(label)
			self._populate_heatmap_grid(
				cell_props_list, panel.grid_layout, panel.cell_widgets,
				prop_key, cmap, panel.colorbar, label, cell_size=cell_size,
				value_range=self._multistep_global_ranges.get(prop_key),
			)

	def _on_multistep_slider_changed(self, value: int) -> None:
		self._populate_multistep_panels(value)

	def _on_multistep_panel_combo_changed(self) -> None:
		self._populate_multistep_panels(self.cmp_step_slider.value())

	def _multistep_step_to(self, target: str) -> None:
		if self._run_result is None or not self._run_result.steps:
			return
		n_steps = len(self._run_result.steps)
		cur = self.cmp_step_slider.value()
		new_val = max(0, cur - 1) if target == "prev" else min(n_steps - 1, cur + 1)
		self.cmp_step_slider.setValue(new_val)

	def _multistep_play_toggle(self) -> None:
		if self._multistep_timer.isActive():
			self._multistep_stop_playback()
			return
		if self._run_result is None or len(self._run_result.steps) <= 1:
			return
		self.cmp_play_btn.setText("⏸")
		self._multistep_timer.start()

	def _multistep_stop_playback(self) -> None:
		self._multistep_timer.stop()
		self.cmp_play_btn.setText("▶")

	def _multistep_timer_tick(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._multistep_stop_playback()
			return
		n_steps = len(self._run_result.steps)
		next_idx = self.cmp_step_slider.value() + 1
		if next_idx >= n_steps:
			next_idx = 0
		self.cmp_step_slider.setValue(next_idx)

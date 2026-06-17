from __future__ import annotations

import math

from PySide6.QtCore import Qt, QPointF, QRect, QRectF, QSize, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QLinearGradient, QPolygonF
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QProgressBar,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QSpinBox,
	QSplitter,
	QStyledItemDelegate,
	QTabWidget,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult, TimeStepResult
from modules.results_service import get_run_summary, get_all_cell_properties


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
	fg = QColor("#f8fafc") # Clean off-white text for dark theme contrast

	return bg, fg


# ── Colorbar Widget ───────────────────────────────────────────────────────────

class _ColorbarWidget(QWidget):
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
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

	def paintEvent(self, event) -> None:
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		w = self.width()
		h = self.height()

		# Draw label
		font = QFont("Segoe UI", 8)
		painter.setFont(font)
		painter.setPen(QColor("#536c80"))

		title = f"Skala: {self.label}"
		painter.drawText(QRectF(0, 0, w, 15), Qt.AlignmentFlag.AlignCenter, title)

		# Draw color bar
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
		painter.setPen(QPen(QColor("#cbdceb"), 1))
		painter.drawRect(bar_margin, bar_y, bar_w, bar_h)

		# Draw min/max text labels
		min_txt = f"{self.vmin:.4e}" if abs(self.vmin) < 1e-2 or abs(self.vmin) >= 1e4 else f"{self.vmin:.4f}"
		max_txt = f"{self.vmax:.4e}" if abs(self.vmax) < 1e-2 or abs(self.vmax) >= 1e4 else f"{self.vmax:.4f}"

		painter.setPen(QColor("#334e68"))
		painter.drawText(QRectF(bar_margin, bar_y + bar_h + 2, 100, 12), Qt.AlignmentFlag.AlignLeft, min_txt)
		painter.drawText(QRectF(w - bar_margin - 100, bar_y + bar_h + 2, 100, 12), Qt.AlignmentFlag.AlignRight, max_txt)

		painter.end()


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
		self.lbl_val.setText(fmt_str.format(value))

		# Scale fonts based on cell dimensions
		fs_num = 10 if w >= 100 else (8 if w >= 75 else 7)
		fs_val = 11 if w >= 100 else (9 if w >= 75 else 8)

		font_num = QFont("Segoe UI", fs_num)
		font_num.setBold(True)
		self.lbl_num.setFont(font_num)

		font_val = QFont("Segoe UI", fs_val)
		font_val.setBold(True)
		self.lbl_val.setFont(font_val)

		bg_hex = bg_color.name()
		fg_hex = fg_color.name()

		# Set styling with a clean, dark-mode matching border
		self.setStyleSheet(f"""
			QFrame#heatmapCell {{
				background-color: {bg_hex};
				border: 1.5px solid #334155;
				border-radius: 8px;
			}}
		""")
		self.lbl_num.setStyleSheet(f"color: {fg_hex}; background: transparent;")
		self.lbl_val.setStyleSheet(f"color: {fg_hex}; background: transparent;")



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


def _residuals_close(v1: float, v2: float, rtol: float = 1e-4) -> bool:
	denom = max(abs(v1), abs(v2), 1e-30)
	return abs(v1 - v2) / denom < rtol


def _repolish(widget: QWidget) -> None:
	widget.style().unpolish(widget)
	widget.style().polish(widget)


def _make_card(title: str) -> tuple[QFrame, QLabel]:
	"""Return (card QFrame, title QLabel)."""
	card = QFrame()
	card.setObjectName("resultCard")
	lay = QVBoxLayout(card)
	lay.setContentsMargins(14, 10, 14, 12)
	lay.setSpacing(6)
	hdr = QLabel(title.upper())
	hdr.setObjectName("resultCardTitle")
	sep = QFrame()
	sep.setFrameShape(QFrame.Shape.HLine)
	sep.setObjectName("resultCardSep")
	lay.addWidget(hdr)
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


def _make_stat_card(title: str) -> tuple[QFrame, QLabel]:
	card = QFrame()
	card.setObjectName("resultStatCard")
	lay = QVBoxLayout(card)
	lay.setContentsMargins(12, 10, 12, 10)
	lay.setSpacing(4)
	title_lbl = QLabel(title)
	title_lbl.setObjectName("resultStatTitle")
	value_lbl = QLabel("-")
	value_lbl.setObjectName("resultStatValue")
	value_lbl.setWordWrap(True)
	lay.addWidget(title_lbl)
	lay.addWidget(value_lbl)
	return card, value_lbl


def _clear_layout(lay: QVBoxLayout) -> None:
	while lay.count():
		item = lay.takeAt(0)
		if item.widget():
			item.widget().deleteLater()


# ── Norm Chart ────────────────────────────────────────────────────────────────

class _NormChartWidget(QWidget):
	"""QPainter-based line chart: Norm vs Step."""

	_COLOR_LINE  = QColor("#06b6d4")
	_COLOR_OK    = QColor("#1e6d4e")
	_COLOR_FAIL  = QColor("#b64842")
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
			painter.setPen(QColor("#64748b"))
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
			"dp": QColor("#ef4444"),  # Red
			"dsw": QColor("#3b82f6"), # Blue
			"dsg": QColor("#10b981"), # Green
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
			painter.setPen(QColor("#94a3b8"))

			# Title label
			painter.drawText(QRectF(10, sy0, margin_l - 15, sh), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, title)

			# Draw limits
			painter.drawText(QRectF(margin_l + 4, sy0 + 2, 80, 12), Qt.AlignmentFlag.AlignLeft, f"+{limit:.2e}")
			painter.drawText(QRectF(margin_l + 4, sy1 - 12, 80, 12), Qt.AlignmentFlag.AlignLeft, f"-{limit:.2e}")

		# Draw cell indices on bottom axis
		painter.setPen(QColor("#64748b"))
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

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._data:   list[list[float]] = []
		self._nc      = 0      # number of cell groups (= n_cells)
		self._zoom    = 1.0
		self._maxabs  = 0.0

	# ── public API ───────────────────────────────────────────────────────────

	def set_data(self, data: list[list[float]], n_cells: int,
	             zoom: float = 1.0) -> None:
		self._data   = data
		self._nc     = n_cells
		self._zoom   = zoom
		self._maxabs = max((abs(v) for row in data for v in row), default=0.0)
		self.updateGeometry()
		self.update()

	def set_zoom(self, zoom: float) -> None:
		self._zoom = zoom
		self.updateGeometry()
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




class ResultsPage(QWidget):
	"""Results viewer — grid symmetry checker, residual bars, convergence log."""

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

		# ── Header ──────────────────────────────────────────────────────────
		self._header = QWidget(self)
		self._header.setObjectName("resultHeader")
		_hrow = QHBoxLayout(self._header)
		_hrow.setContentsMargins(20, 14, 20, 14)
		_hrow.setSpacing(10)
		_title = QLabel("Simulation Results", self._header)
		_title.setObjectName("resultTitle")
		self._badge = QLabel("Belum ada run", self._header)
		self._badge.setObjectName("resultBadge")
		self._badge.setProperty("status", "empty")
		_go_run = QPushButton("Go to Run", self._header)
		_go_run.setObjectName("resultActionButton")
		_go_run.setFixedWidth(100)
		_go_run.clicked.connect(self.goToRunRequested)
		_hrow.addWidget(_title)
		_hrow.addWidget(self._badge)
		_hrow.addStretch(1)
		_hrow.addWidget(_go_run)

		# ── Tabs ─────────────────────────────────────────────────────────────
		self._tabs = QTabWidget(self)
		self._tabs.setObjectName("resultTabs")
		self._tabs.tabBar().setObjectName("resultTabBar")
		self._tabs.tabBar().setExpanding(False)
		self._tabs.setDocumentMode(True)
		self._tabs.addTab(self._build_grid_tab(),           "  Grid & Simetri  ")
		self._tabs.addTab(self._build_residual_tab(),       "  Residual  ")
		self._tabs.addTab(self._build_conv_tab(),     "  Konvergensi  ")
		self._tabs.addTab(self._build_jacobian_tab(), "  Jacobian  ")
		self._tabs.addTab(self._build_corrections_tab(), "  Koreksi Newton  ")
		self._tabs.addTab(self._build_properties_tab(), "  Peta Properti  ")
		self._tabs.addTab(self._build_summary_tab(),  "  Summary  ")
		self._tabs.addTab(self._build_retry_tab(),    "  Retry Log  ")

		# ── Root layout ──────────────────────────────────────────────────────
		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(self._tabs, 1)

		# Wire signals
		self.retry_scope_combo.currentIndexChanged.connect(self._refresh_retry_table)
		self.retry_status_combo.currentIndexChanged.connect(self._refresh_retry_table)
		self._well_spin.valueChanged.connect(self._on_well_changed)

		# Build initial grid
		self._rebuild_grid()

	# =========================================================================
	# Tab builders
	# =========================================================================

	def _build_grid_tab(self) -> QWidget:
		w = QWidget()
		w.setObjectName("resultGridTab")
		vlay = QVBoxLayout(w)
		vlay.setContentsMargins(12, 10, 12, 12)
		vlay.setSpacing(8)

		# Controls row
		toolbar = QWidget(w)
		toolbar.setObjectName("resultToolbar")
		ctrl = QHBoxLayout(toolbar)
		ctrl.setContentsMargins(12, 9, 12, 9)
		ctrl.setSpacing(14)
		well_label = QLabel("Well cell (1-indeks):")
		well_label.setObjectName("resultToolbarLabel")
		ctrl.addWidget(well_label)
		self._well_spin = QSpinBox()
		self._well_spin.setObjectName("resultWellSpin")
		self._well_spin.setRange(1, 9999)
		self._well_spin.setValue(1)
		self._well_spin.setFixedWidth(80)
		ctrl.addWidget(self._well_spin)
		ctrl.addStretch(1)
		for kind, text in [
			("well", "Well"),
			("selected", "Dipilih"),
			("symmetric", "Simetris"),
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

		# Splitter: left = grid scroll, right = info cards
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
		self._grid_layout.setSpacing(4)
		self._grid_layout.setContentsMargins(8, 8, 8, 8)
		self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
		self._grid_scroll.setWidget(self._grid_container)

		self._grid_hint = QLabel("Grid aktif: 2 x 1 (XY).")
		self._grid_hint.setObjectName("resultGridHint")
		self._grid_hint.setWordWrap(True)

		left_w = QWidget()
		left_lay = QVBoxLayout(left_w)
		left_lay.setContentsMargins(0, 0, 0, 0)
		left_lay.setSpacing(8)
		left_lay.addWidget(self._grid_hint)
		left_lay.addWidget(self._grid_scroll, 1)
		left_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

		splitter.addWidget(left_w)

		right_w = QWidget()
		right_w.setObjectName("resultInfoPanel")
		right_w.setMinimumWidth(290)
		right_w.setMaximumWidth(430)
		right_lay = QVBoxLayout(right_w)
		right_lay.setContentsMargins(4, 0, 0, 0)
		right_lay.setSpacing(10)

		self._sel_card, self._sel_card_title = _make_card("Sel Dipilih: —")
		self._lbl_sel_p   = _add_row(self._sel_card, "Pressure", "—")
		self._lbl_sel_sw  = _add_row(self._sel_card, "Sw", "—")
		self._lbl_sel_sg  = _add_row(self._sel_card, "Sg", "—")
		self._lbl_sel_res = _add_row(self._sel_card, "Residual", "—")
		right_lay.addWidget(self._sel_card)

		self._sym_card, _ = _make_card("Cek Simetri")
		self._sym_body = QVBoxLayout()
		self._sym_body.setSpacing(5)
		_h = QLabel("Pilih sel untuk melihat cek simetri.")
		_h.setObjectName("resultRowLabel")
		_h.setWordWrap(True)
		self._sym_body.addWidget(_h)
		self._sym_card.layout().addLayout(self._sym_body)
		right_lay.addWidget(self._sym_card)

		right_lay.addStretch(1)
		splitter.addWidget(right_w)
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 0)
		splitter.setSizes([700, 330])
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
		tbar_lay.addWidget(self._resid_status, 1)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(step_lbl)

		self._resid_step_combo = QComboBox()
		self._resid_step_combo.setObjectName("resultResidStepCombo")
		self._resid_step_combo.setMinimumWidth(140)
		self._resid_step_combo.currentIndexChanged.connect(self._on_resid_step_changed)
		tbar_lay.addWidget(self._resid_step_combo)

		vlay.addWidget(toolbar)

		# ── Unified residual table ────────────────────────────────────────────
		card = QFrame()
		card.setObjectName("resultCard")
		card_lay = QVBoxLayout(card)
		card_lay.setContentsMargins(12, 10, 12, 10)
		card_lay.setSpacing(6)

		card_title = QLabel("RESIDUAL PER SEL")
		card_title.setObjectName("resultCardTitle")
		card_lay.addWidget(card_title)

		self._resid_table = QTableWidget()
		self._resid_table.setObjectName("resultResidTable")
		self._resid_table.setColumnCount(4)
		self._resid_table.setHorizontalHeaderLabels(
			["Sel", "Residual Oil", "Residual Water", "Residual Gas"]
		)
		self._resid_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self._resid_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self._resid_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self._resid_table.verticalHeader().setVisible(False)
		self._resid_table.setShowGrid(False)
		rh = self._resid_table.horizontalHeader()
		rh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
		self._resid_table.setColumnWidth(0, 62)
		for col in (1, 2, 3):
			rh.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
		self._resid_table.setAlternatingRowColors(False)
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
		tc_lay.addWidget(tc_title)

		self._conv_table = QTableWidget()
		self._conv_table.setObjectName("resultConvTable")
		self._conv_table.setColumnCount(7)
		self._conv_table.setHorizontalHeaderLabels(
			["Step", "t (hari)", "dt (hari)", "Iterasi", "MaxR", "Norm", "Status"]
		)
		self._conv_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self._conv_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self._conv_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self._conv_table.verticalHeader().setVisible(False)
		self._conv_table.setShowGrid(False)
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
		cc_lay.addWidget(cc_title)
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
		zoom_lbl = QLabel("Zoom:")
		zoom_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(zoom_lbl)

		btn_zoom_out = QPushButton("−")
		btn_zoom_out.setObjectName("resultToolbarBtn")
		btn_zoom_out.setFixedWidth(28)
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
		btn_zoom_in.setToolTip("Zoom in")
		btn_zoom_in.clicked.connect(self._jacobian_zoom_in)
		tbar_lay.addWidget(btn_zoom_in)

		btn_zoom_reset = QPushButton("↺")
		btn_zoom_reset.setObjectName("resultToolbarBtn")
		btn_zoom_reset.setFixedWidth(28)
		btn_zoom_reset.setToolTip("Reset zoom")
		btn_zoom_reset.clicked.connect(self._jacobian_zoom_reset)
		tbar_lay.addWidget(btn_zoom_reset)

		vlay.addWidget(toolbar)

		# ── Canvas inside a scroll area ───────────────────────────────
		self._jacobian_canvas = _JacobianCanvas()

		scroll = QScrollArea()
		scroll.setObjectName("resultJacobianScroll")
		scroll.setWidget(self._jacobian_canvas)
		scroll.setWidgetResizable(False)   # canvas owns its sizeHint
		scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

		vlay.addWidget(scroll, 1)
		return w

	def _on_jacobian_step_changed(self) -> None:
		self._populate_jacobian_display()

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

		z = _JACOBIAN_ZOOM_STEPS[self._jacobian_zoom_idx]
		self._jacobian_canvas.set_data(display_data, n_cells, z)

		n = len(display_data)
		max_abs = max((abs(v) for row in display_data for v in row), default=0.0)
		self._jacobian_status.setText(
			f"Step {idx + 1}  ·  {n}×{n}  ·  {n_cells} sel  ·  Max |J|: {max_abs:.4e}"
		)

	def _get_jacobian_cell_color(self, val: float, max_abs: float) -> tuple[QColor, QColor]:
		"""
		Light-background diverging palette matching the header blue theme.
		  Zero     → slate-50  (#f8fafc)  muted text
		  Positive → blue-100  → blue-500 → blue-900
		  Negative → rose-100  → rose-500 → rose-900
		  Text     → cyan (#0891b2) on light cells, white on dark cells
		"""
		import math

		if max_abs <= 0.0 or abs(val) < 1e-30:
			return QColor("#f0f9ff"), QColor("#94a3b8")

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
		fg = QColor("#0891b2") if brightness > 180 else QColor("#f8fafc")
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

	def _jacobian_zoom_in(self) -> None:
		if self._jacobian_zoom_idx < len(_JACOBIAN_ZOOM_STEPS) - 1:
			self._jacobian_zoom_idx += 1
			self._apply_jacobian_zoom()

	def _jacobian_zoom_out(self) -> None:
		if self._jacobian_zoom_idx > 0:
			self._jacobian_zoom_idx -= 1
			self._apply_jacobian_zoom()

	def _jacobian_zoom_reset(self) -> None:
		self._jacobian_zoom_idx = _JACOBIAN_ZOOM_DEFAULT_IDX
		self._apply_jacobian_zoom()

	def _apply_jacobian_zoom(self) -> None:
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
		tc_lay.addWidget(tc_title)

		self.corrections_table = QTableWidget()
		self.corrections_table.setObjectName("resultCorrectionsTable")
		self.corrections_table.setColumnCount(4)
		self.corrections_table.setHorizontalHeaderLabels(["Cell", "δp (psia)", "δSw (frac)", "δSg (frac)"])
		self.corrections_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.corrections_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.corrections_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.corrections_table.verticalHeader().setVisible(False)
		self.corrections_table.setShowGrid(True)

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
		cc_lay.addWidget(cc_title)

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
				item_dp.setForeground(QBrush(QColor("#f87171")))
			self.corrections_table.setItem(i, 1, item_dp)

			item_dsw = QTableWidgetItem(f"{v_dsw:.6e}")
			item_dsw.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			if abs(v_dsw) > 1e-12:
				item_dsw.setForeground(QBrush(QColor("#60a5fa")))
			self.corrections_table.setItem(i, 2, item_dsw)

			item_dsg = QTableWidgetItem(f"{v_dsg:.6e}")
			item_dsg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			if abs(v_dsg) > 1e-12:
				item_dsg.setForeground(QBrush(QColor("#34d399")))
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

		self.summary_label = QLabel("Belum ada hasil run.")
		self.summary_label.setObjectName("resultStatusLine")
		self.summary_label.setWordWrap(True)
		vlay.addWidget(self.summary_label)

		stats_grid = QGridLayout()
		stats_grid.setContentsMargins(0, 0, 0, 0)
		stats_grid.setHorizontalSpacing(10)
		stats_grid.setVerticalSpacing(10)

		card_steps, self._sum_steps = _make_stat_card("Steps")
		card_time, self._sum_time = _make_stat_card("Final Time")
		card_conv, self._sum_converged = _make_stat_card("Converged")
		card_maxr, self._sum_maxr = _make_stat_card("Max Residual")
		card_att, self._sum_attempts = _make_stat_card("Attempts")
		card_rej, self._sum_rejected = _make_stat_card("Rejected")

		stats_grid.addWidget(card_steps, 0, 0)
		stats_grid.addWidget(card_time, 0, 1)
		stats_grid.addWidget(card_conv, 0, 2)
		stats_grid.addWidget(card_maxr, 1, 0)
		stats_grid.addWidget(card_att, 1, 1)
		stats_grid.addWidget(card_rej, 1, 2)
		vlay.addLayout(stats_grid)

		phase_card, _ = _make_card("Residual Per Fase")
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
		self.retry_stats_label.setObjectName("resultRowLabel")
		toolbar = QHBoxLayout()
		scope_lbl = QLabel("Scope:")
		scope_lbl.setObjectName("resultToolbarLabel")
		toolbar.addWidget(scope_lbl)
		toolbar.addWidget(self.retry_scope_combo)
		status_lbl = QLabel("Status:")
		status_lbl.setObjectName("resultToolbarLabel")
		toolbar.addWidget(status_lbl)
		toolbar.addWidget(self.retry_status_combo)
		toolbar.addStretch(1)
		toolbar.addWidget(self.retry_stats_label)
		vlay.addLayout(toolbar)
		self.retry_table = QTableWidget(0, 7)
		self.retry_table.setObjectName("resultRetryTable")
		self.retry_table.setHorizontalHeaderLabels(
			["Step", "Retry", "Target Time (days)", "dt (days)",
			 "Max Residual", "Residual Norm", "Status"]
		)
		self.retry_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.retry_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
		self.retry_table.setSortingEnabled(True)
		self.retry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.retry_table.verticalHeader().setVisible(False)
		vlay.addWidget(self.retry_table)
		return w

	# =========================================================================
	# Grid widget
	# =========================================================================

	def _rebuild_grid(self) -> None:
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
				btn.setFixedSize(58, 58)
				btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
				btn.clicked.connect(lambda _=False, cell=n: self._select_cell(cell))
				self._cell_btns[n] = btn
				self._grid_layout.addWidget(
					btn,
					row,
					col,
					Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
				)

		total = max(self._nx * self._ny, 1)
		self._well_spin.setRange(1, total)
		self._well_cell = min(self._well_cell, total)
		self._well_spin.setValue(self._well_cell)
		self._update_grid_hint()
		self._refresh_cell_colors()

	def _refresh_cell_colors(self) -> None:
		step = self._latest_step()
		sym_set = set(
			_symmetric_cells(self._selected_cell, self._well_cell, self._nx, self._ny)
		) if self._selected_cell is not None else set()

		for n, btn in self._cell_btns.items():
			is_well = n == self._well_cell
			is_sel  = n == self._selected_cell
			is_sym  = n in sym_set

			if is_well:
				mode = "well"
			elif is_sel:
				mode = "selected"
			elif is_sym:
				mode = "symmetric"
			else:
				mode = "normal"

			sub = "WELL" if is_well else ("SIM" if is_sym else "")

			if step and step.pressure and n <= len(step.pressure):
				label = f"{n}\n{step.pressure[n - 1]:.0f}"
			else:
				label = str(n)
			if sub:
				label += f"\n{sub}"

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
		self._sel_card_title.setText(f"SEL DIPILIH: {n}  (baris {row + 1}, kol {col + 1})")

		step = self._latest_step()
		if step and step.pressure and n <= len(step.pressure):
			idx = n - 1
			self._lbl_sel_p.setText(f"{step.pressure[idx]:.2f} psia")
			self._lbl_sel_sw.setText(f"{step.sw[idx]:.4f}")
			self._lbl_sel_sg.setText(f"{step.sg[idx]:.4f}")
			res = (
				step.residual_per_cell[idx]
				if step.residual_per_cell and idx < len(step.residual_per_cell)
				else float("nan")
			)
			self._lbl_sel_res.setText(f"{res:.4e}")
		else:
			for lbl in (self._lbl_sel_p, self._lbl_sel_sw, self._lbl_sel_sg, self._lbl_sel_res):
				lbl.setText("—")

	def _update_sym_card(self) -> None:
		n = self._selected_cell
		step = self._latest_step()
		syms = _symmetric_cells(n, self._well_cell, self._nx, self._ny) if n is not None else []

		_clear_layout(self._sym_body)

		if not syms:
			h = QLabel("Tidak ada pasangan simetris untuk sel ini.")
			h.setObjectName("resultRowLabel")
			h.setWordWrap(True)
			self._sym_body.addWidget(h)
			return

		if step is None:
			h = QLabel(
				f"Sel {n} simetris dengan: {', '.join(str(s) for s in syms)}\n\n"
				f"Jalankan simulasi untuk membandingkan residual."
			)
			h.setObjectName("resultRowLabel")
			h.setWordWrap(True)
			self._sym_body.addWidget(h)
			return

		# With simulation data — compare residuals per symmetric pair
		for s in syms:
			pass_check = True
			detail = ""
			if (
				step.residual_per_cell
				and n <= len(step.residual_per_cell)
				and s <= len(step.residual_per_cell)
			):
				v1 = step.residual_per_cell[n - 1]
				v2 = step.residual_per_cell[s - 1]
				pass_check = _residuals_close(v1, v2)
				detail = f"  ({v1:.3e} vs {v2:.3e})"

			icon = "PASS" if pass_check else "FAIL"

			chip = QFrame()
			chip.setObjectName("symCheckChip")
			chip.setProperty("state", "pass" if pass_check else "fail")
			_repolish(chip)
			chip_lay = QHBoxLayout(chip)
			chip_lay.setContentsMargins(8, 5, 8, 5)
			chip_lbl = QLabel(f"{icon}  Sel {n} ↔ Sel {s}{detail}")
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

		def _heat(value: float, scale: float) -> QColor:
			"""Blue (low) → white → red (high) intensity."""
			f = min(abs(value) / max(scale, 1e-30), 1.0)
			if f < 0.5:
				t = f * 2
				r = int(210 + t * (255 - 210))
				g = int(230 + t * (255 - 230))
				b = int(250 + t * (255 - 250))
			else:
				t = (f - 0.5) * 2
				r = 255
				g = int(255 - t * (255 - 180))
				b = int(255 - t * 255)
			return QColor(r, g, b)

		self._resid_table.setRowCount(n_cells)
		for i in range(n_cells):
			v_oil   = oil[i]   if i < len(oil)   else 0.0
			v_water = water[i] if i < len(water) else 0.0
			v_gas   = gas[i]   if i < len(gas)   else 0.0

			cell_item = QTableWidgetItem(f"Sel {i + 1}")
			cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self._resid_table.setItem(i, 0, cell_item)

			for col, val, mx in [(1, v_oil, max_oil), (2, v_water, max_water), (3, v_gas, max_gas)]:
				it = QTableWidgetItem(f"{val:.4e}")
				it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				it.setBackground(_heat(val, mx))
				self._resid_table.setItem(i, col, it)

	def _refresh_residual_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._resid_status.setText("Jalankan simulasi dulu.")
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
			f"{n_cells} sel  ·  "
			f"Max Oil {step.max_oil_residual:.3e}  "
			f"Water {step.max_water_residual:.3e}  "
			f"Gas {step.max_gas_residual:.3e}  "
			f"{'✓ konvergen' if converged else '✗ belum konvergen'}"
		)
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

		_COLOR_GREEN_BG = QColor("#d6f5e8")
		_COLOR_RED_BG   = QColor("#fde8e6")
		_COLOR_GREEN_FG = QColor("#1e6d4e")
		_COLOR_RED_FG   = QColor("#b64842")
		_COLOR_HEADER   = QColor("#536c80")

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
						item.setBackground(QColor("#064e3b"))
					elif sv == "abort-min-dt":
						item.setBackground(QColor("#450a0a"))
					else:
						item.setBackground(QColor("#78350f"))
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
		if cells_xy <= 4:
			self._grid_hint.setText(
				f"Grid aktif: {self._nx} x {self._ny} (XY). Jadi sel yang tampil memang sedikit. "
				f"Untuk uji simetri dosen (5x5), ubah dulu grid di halaman Grid."
			)
		else:
			self._grid_hint.setText(
				f"Grid aktif: {self._nx} x {self._ny} (XY) — klik sel untuk cek pasangan simetri terhadap well."
			)

	# =========================================================================
	# Public API
	# =========================================================================

	def set_project(self, project_config: ProjectConfig) -> None:
		"""Update grid dimensions from project. Rebuilds grid if size changed."""
		self.project_config = project_config
		gs = project_config.grid_spec
		changed = (gs.nx != self._nx or gs.ny != self._ny)
		self._nx = gs.nx
		self._ny = gs.ny
		# Default well to centre of XY plane
		cx = max(gs.nx // 2, 0)
		cy = max(gs.ny // 2, 0)
		self._well_cell = cy * gs.nx + cx + 1
		if changed:
			self._rebuild_grid()
		else:
			self._update_grid_hint()

	def set_run_result(self, run_result: RunResult | None) -> None:
		self._run_result = run_result
		self._active_run_result = run_result

		if run_result is None:
			self.summary_label.setText("Belum ada hasil run.")
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
			self._badge.setText("Belum ada run")
			self._badge.setProperty("status", "empty")
			_repolish(self._badge)
			self._refresh_jacobian_tab()
			self._refresh_corrections_tab()
			return

		step_count = len(run_result.steps)
		warn_count = len(run_result.warnings)
		self._badge.setText(f"{step_count} step(s)  •  {warn_count} warning(s)")
		self._badge.setProperty("status", "ok" if not warn_count else "warn")
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
		tbar_lay.addWidget(self._prop_status, 1)

		step_lbl = QLabel("Step:")
		step_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(step_lbl)

		self.prop_step_combo = QComboBox()
		self.prop_step_combo.setObjectName("resultPropStepCombo")
		self.prop_step_combo.setMinimumWidth(140)
		self.prop_step_combo.currentIndexChanged.connect(self._on_prop_step_changed)
		tbar_lay.addWidget(self.prop_step_combo)

		prop_lbl = QLabel("Properti:")
		prop_lbl.setObjectName("resultToolbarLabel")
		tbar_lay.addWidget(prop_lbl)

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
		tbar_lay.addWidget(self.prop_select_combo)

		vlay.addWidget(toolbar)

		# Horizontal splitter
		splitter = QSplitter(Qt.Orientation.Horizontal)
		splitter.setHandleWidth(6)
		splitter.setChildrenCollapsible(False)

		# Left Card: Data Table
		table_card = QFrame()
		table_card.setObjectName("resultCard")
		tc_lay = QVBoxLayout(table_card)
		tc_lay.setContentsMargins(12, 10, 12, 10)
		tc_lay.setSpacing(6)

		tc_title = QLabel("TABEL SEMUA PROPERTI PER CELL")
		tc_title.setObjectName("resultCardTitle")
		tc_lay.addWidget(tc_title)

		self.prop_table = QTableWidget()
		self.prop_table.setObjectName("resultPropTable")
		self._prop_table_headers = [
			"Cell", "i", "j", "p (psia)", "So", "Sw", "Sg", "Bo", "Bw", "Bg",
			"mu_o", "mu_w", "mu_g", "kro", "krw", "krg", "lam_o", "lam_w", "lam_g",
			"rho_o", "rho_w", "rho_g", "Pcow", "Pcgw"
		]
		self.prop_table.setColumnCount(len(self._prop_table_headers))
		self.prop_table.setHorizontalHeaderLabels(self._prop_table_headers)
		self.prop_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.prop_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.prop_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.prop_table.verticalHeader().setVisible(False)
		self.prop_table.setShowGrid(True)
		self.prop_table.setAlternatingRowColors(False)

		ph = self.prop_table.horizontalHeader()
		ph.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		tc_lay.addWidget(self.prop_table, 1)

		splitter.addWidget(table_card)

		# Right Card: Heatmap Grid
		map_card = QFrame()
		map_card.setObjectName("resultCard")
		mc_lay = QVBoxLayout(map_card)
		mc_lay.setContentsMargins(12, 10, 12, 10)
		mc_lay.setSpacing(6)

		self.map_title = QLabel("PETA GRID HEATMAP: p (psia)")
		self.map_title.setObjectName("resultCardTitle")
		mc_lay.addWidget(self.map_title)

		self.prop_grid_scroll = QScrollArea()
		self.prop_grid_scroll.setObjectName("resultGridScroll")
		self.prop_grid_scroll.setWidgetResizable(True)
		self.prop_grid_scroll.setFrameShape(QFrame.Shape.NoFrame)

		self.prop_grid_container = QWidget()
		self.prop_grid_container.setObjectName("resultGridPanel")
		self.prop_grid_layout = QGridLayout(self.prop_grid_container)
		self.prop_grid_layout.setSpacing(6)
		self.prop_grid_layout.setContentsMargins(12, 12, 12, 12)
		self.prop_grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.prop_grid_scroll.setWidget(self.prop_grid_container)
		mc_lay.addWidget(self.prop_grid_scroll, 1)

		self.colorbar_widget = _ColorbarWidget(self)
		mc_lay.addWidget(self.colorbar_widget)

		splitter.addWidget(map_card)

		splitter.setStretchFactor(0, 3)
		splitter.setStretchFactor(1, 2)
		splitter.setSizes([720, 460])

		vlay.addWidget(splitter, 1)
		return w

	def _clear_prop_grid(self) -> None:
		while self.prop_grid_layout.count():
			item = self.prop_grid_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
		self._prop_cell_widgets.clear()

	def _refresh_properties_tab(self) -> None:
		if self._run_result is None or not self._run_result.steps:
			self._prop_status.setText("Jalankan simulasi dulu.")
			self.prop_step_combo.blockSignals(True)
			self.prop_step_combo.clear()
			self.prop_step_combo.blockSignals(False)
			self.prop_table.setRowCount(0)
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

	def _populate_properties_display(self) -> None:
		if self._run_result is None or not self._run_result.steps or self.project_config is None:
			return

		step_idx = self.prop_step_combo.currentIndex()
		if step_idx < 0 or step_idx >= len(self._run_result.steps):
			return

		step = self._run_result.steps[step_idx]
		cell_props_list = get_all_cell_properties(self.project_config, step)

		# 1. Populate Table
		self.prop_table.setRowCount(len(cell_props_list))

		fmts = {
			"pressure_psia": "{:.2f}",
			"so": "{:.5f}", "sw": "{:.5f}", "sg": "{:.5f}",
			"bo": "{:.6f}", "bw": "{:.6f}", "bg": "{:.6f}",
			"mu_o": "{:.5f}", "mu_w": "{:.5f}", "mu_g": "{:.5f}",
			"kro": "{:.5f}", "krw": "{:.5f}", "krg": "{:.5f}",
			"lam_o": "{:.6f}", "lam_w": "{:.6f}", "lam_g": "{:.6f}",
			"rho_o": "{:.3f}", "rho_w": "{:.3f}", "rho_g": "{:.3f}",
			"pcow": "{:.4f}", "pcgw": "{:.4f}",
		}

		# Determine min and max for scaling colormaps
		prop_minmax = {}
		for key in fmts.keys():
			vals = [r[key] for r in cell_props_list]
			prop_minmax[key] = (min(vals), max(vals))

		prop_colormaps = {
			"pressure_psia": "plasma",
			"so": "YlOrRd",
			"sw": "Blues",
			"sg": "Greens",
			"bo": "autumn",
			"bw": "winter",
			"bg": "copper",
			"mu_o": "hot",
			"mu_w": "cool",
			"mu_g": "viridis",
			"kro": "YlOrRd",
			"krw": "Blues",
			"krg": "Greens",
			"lam_o": "plasma",
			"lam_w": "plasma",
			"lam_g": "plasma",
			"rho_o": "hot",
			"rho_w": "cool",
			"rho_g": "viridis",
			"pcow": "YlOrRd",
			"pcgw": "Greens",
		}

		for r, cell_data in enumerate(cell_props_list):
			cell_no = cell_data["cell"]
			i_val = cell_data["i_index"]
			j_val = cell_data["j_index"]

			item_cell = QTableWidgetItem(f"Sel {cell_no}")
			item_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.prop_table.setItem(r, 0, item_cell)

			item_i = QTableWidgetItem(str(i_val))
			item_i.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.prop_table.setItem(r, 1, item_i)

			item_j = QTableWidgetItem(str(j_val))
			item_j.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			self.prop_table.setItem(r, 2, item_j)

			for col_idx, col_header in enumerate(self._prop_table_headers[3:], start=3):
				prop_key = self._properties_meta[col_idx - 3][0]
				val = cell_data[prop_key]
				fmt = fmts.get(prop_key, "{:.4f}")

				item = QTableWidgetItem(fmt.format(val))
				item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				item.setForeground(QBrush(QColor("#cbd5e1")))
				self.prop_table.setItem(r, col_idx, item)

		# 2. Populate Heatmap Grid
		self._clear_prop_grid()

		selected_prop_idx = self.prop_select_combo.currentIndex()
		if selected_prop_idx < 0:
			return

		prop_key, prop_cmap = self.prop_select_combo.currentData()
		prop_label = self.prop_select_combo.currentText()

		self.map_title.setText(f"PETA GRID HEATMAP: {prop_label}")

		prop_vals = [cell_data[prop_key] for cell_data in cell_props_list]
		vmin = min(prop_vals)
		vmax = max(prop_vals)

		self.colorbar_widget.set_scale(vmin, vmax, prop_cmap, prop_label)
		fmt_str = fmts.get(prop_key, "{:.4f}")

		n_cells = len(cell_props_list)
		cell_w = 120 if n_cells <= 16 else (80 if n_cells <= 100 else 55)
		cell_h = 100 if n_cells <= 16 else (70 if n_cells <= 100 else 50)

		for cell_data in cell_props_list:
			cell_no = cell_data["cell"]
			i_val = cell_data["i_index"]
			j_val = cell_data["j_index"]
			val = cell_data[prop_key]

			bg_color, fg_color = get_color_from_colormap(val, vmin, vmax, prop_cmap)

			cell_widget = _HeatmapCellWidget(cell_no)
			cell_widget.update_cell(val, bg_color, fg_color, fmt_str, cell_w, cell_h)

			self._prop_cell_widgets[cell_no] = cell_widget
			self.prop_grid_layout.addWidget(cell_widget, j_val, i_val)

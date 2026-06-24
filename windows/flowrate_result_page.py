from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
	QAbstractItemView,
	QFrame,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QTableWidget,
	QTableWidgetItem,
	QTabWidget,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult
from modules.results_service import get_well_rates_per_step


def _title_row(title_label: QLabel) -> QHBoxLayout:
	row = QHBoxLayout()
	row.setContentsMargins(0, 0, 0, 0)
	row.setSpacing(0)
	row.addWidget(title_label, 1)
	return row


# ── Result rate plot (Qo/Qw/Qg vs time) ───────────────────────────────────────
# Same paint/interaction model as _PVTMultiPlotWidget (pvt_page.py) and
# _RockMultiPlotWidget (rock_page.py) -- this codebase gives each page its own
# small, tailored copy of this chart rather than sharing one generic widget --
# so this page's charts look and behave identically to the PVT/Rock ones.

class _RateMultiPlotWidget(QWidget):
	_SURFACE = QColor("#FFFFFF")
	_WORKSPACE = QColor("#F7F9FB")
	_BORDER = QColor("#D7DEE7")
	_BORDER_STRONG = QColor("#B8C3D1")
	_TEXT = QColor("#1F2937")
	_MUTED = QColor("#5B6676")
	_GRIDLINE = QColor("#DDE4EC")
	_PRIMARY = QColor("#0F5C8E")
	_SUCCESS = QColor("#2D6A4F")
	_WARNING = QColor("#A86A15")
	_DANGER = QColor("#B2413F")
	# Same phase color convention as PVT's Bo/Bw/Bg: oil=amber, water=blue, gas=teal.
	_COLORS = {
		"qo": QColor("#B7791F"),
		"qw": QColor("#2563A6"),
		"qg": QColor("#0F766E"),
	}

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._series: list[dict[str, object]] = []
		self._hit_points: list[dict[str, object]] = []
		self._hover_hit: dict[str, object] | None = None
		self._selected_hit: dict[str, object] | None = None
		self.setMouseTracking(True)
		self.setCursor(Qt.CursorShape.CrossCursor)
		self.setMinimumHeight(420)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	def set_series(self, series: list[dict[str, object]]) -> None:
		self._series = series
		self._hover_hit = None
		self._selected_hit = None
		self.update()

	def sizeHint(self) -> QSize:
		return QSize(980, self.minimumHeight())

	def mouseMoveEvent(self, event) -> None:
		self._hover_hit = self._nearest_hit(event.position())
		self.setToolTip(self._hit_tooltip(self._hover_hit or self._selected_hit))
		self.update()

	def mousePressEvent(self, event) -> None:
		if event.button() == Qt.MouseButton.LeftButton:
			self._selected_hit = self._nearest_hit(event.position())
			self.setToolTip(self._hit_tooltip(self._selected_hit))
			self.update()
		elif event.button() == Qt.MouseButton.RightButton:
			self._selected_hit = None
			self.setToolTip(self._hit_tooltip(self._hover_hit))
			self.update()

	def leaveEvent(self, event) -> None:
		self._hover_hit = None
		self.setToolTip("")
		self.update()

	def _nearest_hit(self, pos: QPointF) -> dict[str, object] | None:
		best_hit = None
		best_distance = 14.0
		for hit in self._hit_points:
			pt = hit["point"]
			if not isinstance(pt, QPointF):
				continue
			distance = ((pt.x() - pos.x()) ** 2 + (pt.y() - pos.y()) ** 2) ** 0.5
			if distance < best_distance:
				best_distance = distance
				best_hit = hit
		return best_hit

	def paintEvent(self, event) -> None:
		p = QPainter(self)
		p.setRenderHint(QPainter.RenderHint.Antialiasing)
		p.fillRect(self.rect(), self._WORKSPACE)

		if not self._series:
			p.setPen(self._MUTED)
			p.setFont(QFont("Segoe UI", 9))
			p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Jalankan simulasi dulu.")
			p.end()
			return

		self._hit_points = []
		rect = self.rect().adjusted(14, 12, -14, -14)
		for item in self._series:
			self._draw_panel(p, QRectF(rect), item)
		self._draw_interaction_overlay(p)
		p.end()

	def _draw_panel(self, p: QPainter, rect: QRectF, item: dict[str, object]) -> None:
		key = str(item["key"])
		label = str(item["label"])
		x_label = str(item["x_label"])
		points = item["points"]
		if not isinstance(points, list) or not points:
			return
		line = self._COLORS.get(key, QColor("#0F5C8E"))
		label_main, _, label_detail = label.partition("(")
		label_main = label_main.strip()
		label_detail = f"({label_detail}" if label_detail else "Laju alir vs waktu"

		p.setPen(QPen(self._BORDER, 1))
		p.setBrush(self._SURFACE)
		p.drawRoundedRect(rect, 8, 8)

		p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
		p.setPen(self._TEXT)
		p.drawText(QRectF(rect.left() + 16, rect.top() + 18, rect.width() - 180, 28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label_main)
		p.setFont(QFont("Segoe UI", 8))
		p.setPen(self._MUTED)
		p.drawText(QRectF(rect.left() + 16, rect.top() + 48, rect.width() - 180, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label_detail)

		plot = rect.adjusted(72, 92, -28, -68)
		if plot.width() <= 20 or plot.height() <= 20:
			return

		xs = [float(x) for x, _ in points]
		ys = [float(y) for _, y in points]
		xmin, xmax = min(xs), max(xs)
		ymin, ymax = min(ys), max(ys)
		if abs(xmax - xmin) < 1e-12:
			xmax = xmin + 1.0
		if abs(ymax - ymin) < 1e-12:
			ymax = ymin + 1.0
		ypad = (ymax - ymin) * 0.08
		ymin -= ypad
		ymax += ypad
		trend_txt, _ = self._trend_label(ys)
		range_txt = f"{min(ys):.3g} to {max(ys):.3g}"

		p.setPen(QPen(self._BORDER, 1))
		p.setBrush(QColor("#FBFCFD"))
		p.drawRoundedRect(plot, 8, 8)
		p.setPen(QPen(self._GRIDLINE, 1))
		for i in range(5):
			y = plot.top() + i * plot.height() / 4
			p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
		for i in range(3):
			x = plot.left() + i * plot.width() / 2
			p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

		def to_pt(x: float, y: float) -> QPointF:
			px = plot.left() + (x - xmin) / (xmax - xmin) * plot.width()
			py = plot.bottom() - (y - ymin) / (ymax - ymin) * plot.height()
			return QPointF(px, py)

		plot_points = [(x, y, to_pt(x, y)) for x, y in points]
		p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
		p.setPen(self._PRIMARY)
		p.drawText(QRectF(rect.right() - 230, rect.top() + 18, 214, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, trend_txt)
		p.setFont(QFont("Segoe UI", 8))
		p.setPen(self._MUTED)
		p.drawText(QRectF(rect.right() - 230, rect.top() + 42, 214, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, range_txt)

		p.setPen(QPen(line, 2.4))
		for (_, _, a), (_, _, b) in zip(plot_points, plot_points[1:]):
			p.drawLine(a, b)
		p.setBrush(line)
		p.setPen(QPen(self._SURFACE, 1))
		for time_days, value, pt in plot_points:
			p.drawEllipse(pt, 4.2, 4.2)
			self._hit_points.append({
				"point": pt,
				"plot": plot,
				"time_days": time_days,
				"value": value,
				"label": label,
				"x_label": x_label,
				"color": line,
			})

		self._draw_axis_labels(p, plot, xmin, xmax, ymin, ymax, x_label)
		p.setPen(QPen(self._BORDER, 1))
		p.setBrush(Qt.BrushStyle.NoBrush)
		p.drawRoundedRect(plot.adjusted(-1, -1, 1, 1), 8, 8)

	def _trend_label(self, values: list[float]) -> tuple[str, QColor]:
		if len(values) < 2:
			return "Single point", self._MUTED
		deltas = [b - a for a, b in zip(values, values[1:])]
		tol = 1e-12
		if all(abs(delta) <= tol for delta in deltas):
			return "Constant", self._MUTED
		if all(delta >= -tol for delta in deltas):
			return "Monotonically increasing", self._SUCCESS
		if all(delta <= tol for delta in deltas):
			return "Monotonically decreasing", self._DANGER
		return "Non-monotonic", self._WARNING

	def _draw_axis_labels(self, p: QPainter, plot: QRectF, xmin: float, xmax: float, ymin: float, ymax: float, x_label: str) -> None:
		p.setFont(QFont("Segoe UI", 7))
		p.setPen(self._MUTED)
		for i in range(5):
			value = ymax - (ymax - ymin) * i / 4
			y = plot.top() + plot.height() * i / 4
			p.drawText(QRectF(plot.left() - 56, y - 7, 48, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:.3g}")
		for i in range(4):
			value = xmin + (xmax - xmin) * i / 3
			x = plot.left() + plot.width() * i / 3
			p.drawText(QRectF(x - 30, plot.bottom() + 6, 60, 14), Qt.AlignmentFlag.AlignCenter, f"{value:.2f}")
		p.setFont(QFont("Segoe UI", 7))
		p.drawText(QRectF(plot.left(), plot.bottom() + 20, plot.width(), 14), Qt.AlignmentFlag.AlignCenter, x_label)

	def _draw_interaction_overlay(self, p: QPainter) -> None:
		hit = self._hover_hit or self._selected_hit
		if not hit:
			return
		pt = hit.get("point")
		plot = hit.get("plot")
		line = hit.get("color")
		if not isinstance(pt, QPointF) or not isinstance(plot, QRectF) or not isinstance(line, QColor):
			return
		p.setPen(QPen(self._BORDER_STRONG, 1, Qt.PenStyle.DashLine))
		p.drawLine(QPointF(pt.x(), plot.top()), QPointF(pt.x(), plot.bottom()))
		p.drawLine(QPointF(plot.left(), pt.y()), QPointF(plot.right(), pt.y()))
		p.setBrush(self._SURFACE)
		p.setPen(QPen(line, 2))
		p.drawEllipse(pt, 6.5, 6.5)

	def _hit_tooltip(self, hit: dict[str, object] | None) -> str:
		if not hit:
			return ""
		label = str(hit.get("label", "Rate"))
		time_days = float(hit.get("time_days", 0.0))
		value = float(hit.get("value", 0.0))
		x_label = str(hit.get("x_label", "Waktu"))
		return (
			f"<div style='font-family:\"Segoe UI\"; font-weight:600;'>{label}</div>"
			f"<div style='font-family:\"Segoe UI\",sans-serif; font-size:8.5pt;'>"
			f"{x_label} = {time_days:.2f} hari<br/>Nilai = {value:.6g}</div>"
		)


class FlowrateResultPage(QWidget):
	"""Standalone top-level page (sibling of Validation) showing field Qo/Qw/Qg
	vs time, each as a Grafik + Tabel pair."""

	goToRunRequested = Signal()

	_RATE_META = (
		("qo", "Qo - Laju Produksi Oil", "STB/day"),
		("qw", "Qw - Laju Produksi Water", "STB/day"),
		("qg", "Qg - Laju Produksi Gas", "Mscf/day"),
	)

	def __init__(self) -> None:
		super().__init__()
		self.project_config: ProjectConfig | None = None
		self._run_result: RunResult | None = None
		self._result_plots: dict[str, _RateMultiPlotWidget] = {}
		self._result_tables: dict[str, QTableWidget] = {}

		self._header = QWidget(self)
		self._header.setObjectName("resultHeader")
		hrow = QHBoxLayout(self._header)
		hrow.setContentsMargins(20, 14, 20, 14)
		hrow.setSpacing(10)
		title = QLabel("Forecast", self._header)
		title.setObjectName("resultTitle")
		go_run = QPushButton("Go to Run", self._header)
		go_run.setObjectName("resultActionButton")
		go_run.setFixedWidth(100)
		go_run.setCursor(Qt.CursorShape.PointingHandCursor)
		go_run.clicked.connect(self.goToRunRequested)
		hrow.addWidget(title)
		hrow.addStretch(1)
		hrow.addWidget(go_run)

		rate_tabs = QTabWidget(self)
		rate_tabs.setObjectName("resultGroupTabs")
		rate_tabs.tabBar().setObjectName("resultGroupTabBar")
		rate_tabs.tabBar().setExpanding(False)
		rate_tabs.setDocumentMode(True)
		for rate_key, rate_title, rate_unit in self._RATE_META:
			rate_tabs.addTab(self._build_rate_subtab(rate_key, rate_title, rate_unit), f"  {rate_key.upper()}  ")

		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(rate_tabs, 1)

	def _build_rate_subtab(self, rate_key: str, rate_title: str, rate_unit: str) -> QWidget:
		"""One sub-tab (e.g. Qo): a nested Grafik/Tabel sub-sub-tab pair, styled
		like the Table/Heatmap split on the Validation page and the Rock/Graph
		split on the Rock-Fluid page."""
		wrap = QWidget()
		wrap_lay = QVBoxLayout(wrap)
		wrap_lay.setContentsMargins(14, 12, 14, 14)
		wrap_lay.setSpacing(10)

		sub_tabs = QTabWidget()
		sub_tabs.setObjectName("subTabs")
		sub_tabs.tabBar().setObjectName("subTabBar")
		sub_tabs.tabBar().setExpanding(False)
		sub_tabs.setDocumentMode(True)

		label = f"{rate_title} ({rate_unit})"

		# Grafik
		graph_card = QFrame()
		graph_card.setObjectName("resultCard")
		g_lay = QVBoxLayout(graph_card)
		g_lay.setContentsMargins(12, 10, 12, 10)
		g_lay.setSpacing(6)
		g_title = QLabel(label.upper())
		g_title.setObjectName("resultCardTitle")
		g_lay.addLayout(_title_row(g_title))

		plot = _RateMultiPlotWidget()
		plot.setObjectName("pvtPlotCanvas")
		plot_scroll = QScrollArea()
		plot_scroll.setObjectName("pvtPlotScroll")
		plot_scroll.setWidgetResizable(True)
		plot_scroll.setFrameShape(QFrame.Shape.NoFrame)
		plot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		plot_scroll.setWidget(plot)
		g_lay.addWidget(plot_scroll, 1)
		sub_tabs.addTab(graph_card, "  Grafik  ")
		self._result_plots[rate_key] = plot

		# Tabel
		table_card = QFrame()
		table_card.setObjectName("resultCard")
		t_lay = QVBoxLayout(table_card)
		t_lay.setContentsMargins(12, 10, 12, 10)
		t_lay.setSpacing(6)
		t_title = QLabel(label.upper())
		t_title.setObjectName("resultCardTitle")
		t_lay.addLayout(_title_row(t_title))

		table = QTableWidget()
		table.setObjectName("dataTable")
		table.setColumnCount(3)
		table.setHorizontalHeaderLabels(["Step", "t (hari)", f"{rate_key.upper()} ({rate_unit})"])
		table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		table.verticalHeader().setVisible(False)
		table.setShowGrid(False)
		table.setAlternatingRowColors(True)
		table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		t_lay.addWidget(table, 1)
		sub_tabs.addTab(table_card, "  Tabel  ")
		self._result_tables[rate_key] = table

		wrap_lay.addWidget(sub_tabs, 1)
		return wrap

	# ── Public API ────────────────────────────────────────────────────────────

	def set_project(self, project_config: ProjectConfig) -> None:
		self.project_config = project_config

	def set_run_result(self, run_result: RunResult | None) -> None:
		self._run_result = run_result
		if run_result is None or not run_result.steps or self.project_config is None:
			for plot in self._result_plots.values():
				plot.set_series([])
			for table in self._result_tables.values():
				table.setRowCount(0)
			return

		rows = get_well_rates_per_step(self.project_config, run_result)
		for rate_key, rate_title, rate_unit in self._RATE_META:
			label = f"{rate_title} ({rate_unit})"
			points = [(r["time_days"], r[rate_key]) for r in rows]
			self._result_plots[rate_key].set_series([{
				"key": rate_key, "label": label, "x_label": "Waktu (hari)", "points": points,
			}])

			table = self._result_tables[rate_key]
			table.setRowCount(len(rows))
			for r, row in enumerate(rows):
				item_step = QTableWidgetItem(str(row["step"]))
				item_step.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				table.setItem(r, 0, item_step)

				item_t = QTableWidgetItem(f"{row['time_days']:.2f}")
				item_t.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				table.setItem(r, 1, item_t)

				item_val = QTableWidgetItem(f"{row[rate_key]:.4f}")
				item_val.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
				table.setItem(r, 2, item_val)

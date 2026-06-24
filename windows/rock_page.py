from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QFileDialog,
	QFrame,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QLineEdit,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QTabWidget,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


def _cell(table: QTableWidget, row: int, col: int, text: str) -> None:
	item = QTableWidgetItem(text)
	item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
	table.setItem(row, col, item)


def _make_table(headers: list[str]) -> QTableWidget:
	t = QTableWidget(0, len(headers))
	t.setObjectName("dataTable")
	t.setHorizontalHeaderLabels(headers)
	t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
	t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
	t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
	t.setAlternatingRowColors(True)
	t.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
	t.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
	t.verticalHeader().setVisible(False)
	hh = t.horizontalHeader()
	hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
	for i in range(1, len(headers)):
		hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
	return t


def _fill_table(
	table: QTableWidget,
	rock_tables: dict[str, list[tuple[float, float]]],
	col_keys: list[str],
	filter_text: str = "",
	) -> int:
	seen: set[float] = set()
	sats: list[float] = []
	for k in col_keys:
		for s, _ in rock_tables.get(k, []):
			if s not in seen:
				seen.add(s)
				sats.append(s)
	sats.sort()
	if filter_text:
		sats = [sat for sat in sats if filter_text in f"{sat:.4f}"]
	lookup = {k: {s: v for s, v in rock_tables.get(k, [])} for k in col_keys}
	table.setRowCount(len(sats))
	for r, sat in enumerate(sats):
		_cell(table, r, 0, f"{sat:.4f}")
		for c, k in enumerate(col_keys, 1):
			val = lookup[k].get(sat)
			_cell(table, r, c, f"{val:.6g}" if val is not None else "—")
	table.resizeRowsToContents()
	return len(sats)


class _RockMultiPlotWidget(QWidget):
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
	_COLORS = {
		"kro": QColor("#B7791F"),
		"krw": QColor("#2563A6"),
		"pcow": QColor("#0F766E"),
		"krg": QColor("#5C6F91"),
		"pcgw": QColor("#A14F49"),
	}

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._series: list[dict[str, object]] = []
		self._hit_points: list[dict[str, object]] = []
		self._hover_hit: dict[str, object] | None = None
		self._selected_hit: dict[str, object] | None = None
		self.setMouseTracking(True)
		self.setCursor(Qt.CursorShape.CrossCursor)
		self.setMinimumHeight(620)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	def set_series(self, series: list[dict[str, object]]) -> None:
		self._series = series
		self._hover_hit = None
		self._selected_hit = None
		self._update_canvas_height()
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

	def _update_canvas_height(self) -> None:
		count = len(self._series)
		if count <= 0:
			height = 620
		else:
			cols = self._column_count(count)
			rows = (count + cols - 1) // cols
			panel_height = 430 if cols >= 2 else 520
			height = 36 + rows * panel_height + max(0, rows - 1) * 24
		self.setMinimumHeight(height)
		self.updateGeometry()

	def _column_count(self, count: int) -> int:
		if count <= 1:
			return 1
		return 2 if self.width() >= 1700 else 1

	def paintEvent(self, event) -> None:
		p = QPainter(self)
		p.setRenderHint(QPainter.RenderHint.Antialiasing)
		p.fillRect(self.rect(), self._WORKSPACE)

		if not self._series:
			p.setPen(self._MUTED)
			p.setFont(QFont("Segoe UI", 9))
			p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Belum ada data rock-fluid untuk diplot")
			p.end()
			return

		self._hit_points = []
		count = len(self._series)
		cols = self._column_count(count)
		rows = (count + cols - 1) // cols
		outer = self.rect().adjusted(14, 12, -14, -14)
		gap = 22
		panel_w = (outer.width() - gap * (cols - 1)) / cols
		panel_h = (outer.height() - gap * (rows - 1)) / rows

		for idx, item in enumerate(self._series):
			col = idx % cols
			row = idx // cols
			rect = QRectF(
				outer.left() + col * (panel_w + gap),
				outer.top() + row * (panel_h + gap),
				panel_w,
				panel_h,
			)
			self._draw_panel(p, rect, item)
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
		label_detail = f"({label_detail}" if label_detail else "Rock-fluid curve"

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
		for saturation, value, pt in plot_points:
			p.drawEllipse(pt, 4.2, 4.2)
			self._hit_points.append({
				"point": pt,
				"plot": plot,
				"saturation": saturation,
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

	def _draw_badge(self, p: QPainter, rect: QRectF, text: str, ink: QColor, fill: QColor, border: QColor) -> None:
		radius = rect.height() / 2
		p.setPen(QPen(border, 1))
		p.setBrush(fill)
		p.drawRoundedRect(rect, radius, radius)
		p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
		p.setPen(ink)
		p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

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
		label = str(hit.get("label", "Rock"))
		saturation = float(hit.get("saturation", 0.0))
		value = float(hit.get("value", 0.0))
		x_label = str(hit.get("x_label", "Saturation"))
		return (
			f"<div style='font-family:\"Segoe UI\"; font-weight:600;'>{label}</div>"
			f"<div style='font-family:\"Segoe UI\",sans-serif; font-size:8.5pt;'>"
			f"{x_label} = {saturation:.4f}<br/>Nilai = {value:.6g}</div>"
		)


class RockPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()
	importFileRequested = Signal(str)

	# Water-Oil columns: index = Sw
	_WO_KEYS = [("kro", "Kro"), ("krw", "Krw"), ("pcow", "Pcow\n(psia)")]
	# Gas columns: index = Sg
	_GAS_KEYS = [("krg", "Krg"), ("pcgw", "Pcgw\n(psia)")]
	_SYSTEM_OPTIONS = {
		"All Systems": ("wo", "gas"),
		"Water-Oil": ("wo",),
		"Gas": ("gas",),
	}
	_GRAPH_META = {
		"kro": ("Oil Relative Permeability (Kro)", "Sw"),
		"krw": ("Water Relative Permeability (Krw)", "Sw"),
		"pcow": ("Oil-Water Capillary Pressure (Pcow)", "Sw"),
		"krg": ("Gas Relative Permeability (Krg)", "Sg"),
		"pcgw": ("Gas-Water Capillary Pressure (Pcgw)", "Sg"),
	}

	def __init__(self) -> None:
		super().__init__()
		self._rock_tables: dict[str, list[tuple[float, float]]] = {}
		outer = QVBoxLayout(self)
		outer.setContentsMargins(0, 0, 0, 0)
		outer.setSpacing(0)
		scroll = QScrollArea(self)
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		outer.addWidget(scroll)
		content = QWidget()
		scroll.setWidget(content)
		root = QVBoxLayout(content)
		root.setSpacing(12)
		root.setContentsMargins(18, 16, 18, 18)

		# ── Header row ────────────────────────────────────────────────
		hdr = QHBoxLayout()
		hdr.setSpacing(12)
		title_block = QVBoxLayout()
		title_block.setSpacing(3)
		title = QLabel("Rock & Fluid Properties")
		title.setObjectName("pageTitle")
		subtitle = QLabel("Review relative-permeability and capillary-pressure tables for the active flow systems.")
		subtitle.setObjectName("pageSubtitle")
		self._status = QLabel("Belum ada data.")
		self._status.setObjectName("pageStatusChip")
		self._status.hide()
		title_block.addWidget(title)
		title_block.addWidget(subtitle)
		hdr.addLayout(title_block)
		hdr.addStretch()
		root.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		root.addWidget(sep)

		actions_panel = QFrame()
		actions_panel.setObjectName("pageSectionPanel")
		actions_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		actions_root = QVBoxLayout(actions_panel)
		actions_root.setContentsMargins(12, 10, 12, 10)
		actions_root.setSpacing(4)

		# ── Button row ────────────────────────────────────────────────
		btn_row = QHBoxLayout()
		btn_row.setSpacing(6)
		self.import_button = QPushButton("Import CSV / Excel")
		self.import_button.setObjectName("pvtPrimaryButton")
		self.load_button = QPushButton("Load Contoh Rock-Fluid")
		self.load_button.setObjectName("pvtSecondaryButton")
		self.clear_button = QPushButton("Hapus Rock-Fluid")
		self.clear_button.setObjectName("pvtDangerButton")
		for b in (self.import_button, self.load_button, self.clear_button):
			b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
			b.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_row.addWidget(self.import_button)
		btn_row.addWidget(self.load_button)
		btn_row.addWidget(self.clear_button)
		btn_row.addStretch()
		actions_root.addLayout(btn_row)
		self.import_feedback = QLabel("")
		self.import_feedback.setObjectName("pageFeedback")
		self.import_feedback.setWordWrap(True)
		self.import_feedback.setVisible(False)
		actions_root.addWidget(self.import_feedback)
		root.addWidget(actions_panel)

		table_panel = QFrame()
		table_panel.setObjectName("pageSectionPanel")
		table_root = QVBoxLayout(table_panel)
		table_root.setContentsMargins(16, 14, 16, 16)
		table_root.setSpacing(8)
		table_header = QHBoxLayout()
		table_title = QLabel("Rock-Fluid Table Preview")
		table_title.setObjectName("pageSectionTitle")
		table_header.addWidget(table_title)
		table_header.addStretch()
		table_root.addLayout(table_header)
		self._empty_note = QLabel("Load the example rock-fluid dataset to inspect water-oil and gas-system tables.")
		self._empty_note.setObjectName("pageEmptyNote")
		self._empty_note.setWordWrap(True)
		table_root.addWidget(self._empty_note)

		controls_card = QFrame()
		controls_card.setObjectName("pageSubPanel")
		controls_row = QHBoxLayout(controls_card)
		controls_row.setContentsMargins(14, 12, 14, 12)
		controls_row.setSpacing(10)
		controls_row.addWidget(self._make_control_label("System"))
		self.system_picker = QComboBox()
		self.system_picker.setObjectName("pageCompactControl")
		self.system_picker.addItems(self._SYSTEM_OPTIONS.keys())
		controls_row.addWidget(self.system_picker)
		controls_row.addWidget(self._make_control_label("Saturation Filter"))
		self.saturation_filter = QLineEdit()
		self.saturation_filter.setObjectName("pageCompactField")
		self.saturation_filter.setPlaceholderText("e.g. 0.25")
		controls_row.addWidget(self.saturation_filter)
		controls_row.addStretch()
		table_root.addWidget(controls_card)

		# ── Water-Oil table ───────────────────────────────────────────
		self.wo_section = QFrame()
		self.wo_section.setObjectName("pageTableSection")
		wo_section_root = QVBoxLayout(self.wo_section)
		wo_section_root.setContentsMargins(0, 0, 0, 0)
		wo_section_root.setSpacing(6)
		wo_label = QLabel("Water-Oil System")
		wo_label.setObjectName("tableGroupLabel")
		wo_section_root.addWidget(wo_label)
		self.wo_table = _make_table(["Sw"] + [h for _, h in self._WO_KEYS])
		self.wo_table.setMinimumHeight(170)
		self.wo_table.setMaximumHeight(320)
		wo_section_root.addWidget(self.wo_table)
		table_root.addWidget(self.wo_section)

		# ── Gas table ─────────────────────────────────────────────────
		self.gas_section = QFrame()
		self.gas_section.setObjectName("pageTableSection")
		gas_section_root = QVBoxLayout(self.gas_section)
		gas_section_root.setContentsMargins(0, 0, 0, 0)
		gas_section_root.setSpacing(6)
		gas_label = QLabel("Gas System")
		gas_label.setObjectName("tableGroupLabel")
		gas_section_root.addWidget(gas_label)
		self.gas_table = _make_table(["Sg"] + [h for _, h in self._GAS_KEYS])
		self.gas_table.setMinimumHeight(150)
		self.gas_table.setMaximumHeight(300)
		gas_section_root.addWidget(self.gas_table)
		table_root.addWidget(self.gas_section)

		graph_panel = QFrame()
		graph_panel.setObjectName("pageSectionPanel")
		graph_root = QVBoxLayout(graph_panel)
		graph_root.setContentsMargins(16, 14, 16, 16)
		graph_root.setSpacing(10)
		graph_header = QHBoxLayout()
		graph_title = QLabel("Rock-Fluid Curves")
		graph_title.setObjectName("pageSectionTitle")
		graph_hint = QLabel("Hover titik untuk inspect nilai; left-click lock marker, right-click clear.")
		graph_hint.setObjectName("pageHintLabel")
		graph_header.addWidget(graph_title)
		graph_header.addStretch()
		graph_header.addWidget(graph_hint)
		graph_root.addLayout(graph_header)

		graph_controls = QFrame()
		graph_controls.setObjectName("pageSubPanel")
		graph_controls_row = QHBoxLayout(graph_controls)
		graph_controls_row.setContentsMargins(14, 12, 14, 12)
		graph_controls_row.setSpacing(10)
		graph_controls_row.addWidget(self._make_control_label("System"))
		self.graph_system_picker = QComboBox()
		self.graph_system_picker.setObjectName("pageCompactControl")
		self.graph_system_picker.addItems(self._SYSTEM_OPTIONS.keys())
		graph_controls_row.addWidget(self.graph_system_picker)
		graph_controls_row.addWidget(self._make_control_label("Saturation Filter"))
		self.graph_saturation_filter = QLineEdit()
		self.graph_saturation_filter.setObjectName("pageCompactField")
		self.graph_saturation_filter.setPlaceholderText("e.g. 0.25")
		graph_controls_row.addWidget(self.graph_saturation_filter)
		graph_controls_row.addStretch()
		graph_root.addWidget(graph_controls)

		self.rock_plot = _RockMultiPlotWidget()
		self.rock_plot.setObjectName("pvtPlotCanvas")
		plot_scroll = QScrollArea()
		plot_scroll.setObjectName("pvtPlotScroll")
		plot_scroll.setWidgetResizable(True)
		plot_scroll.setFrameShape(QFrame.Shape.NoFrame)
		plot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		plot_scroll.setWidget(self.rock_plot)
		graph_root.addWidget(plot_scroll, 1)

		self.rock_tabs = QTabWidget()
		self.rock_tabs.setObjectName("subTabs")
		self.rock_tabs.tabBar().setObjectName("subTabBar")
		self.rock_tabs.tabBar().setExpanding(False)
		self.rock_tabs.setDocumentMode(True)
		self.rock_tabs.addTab(table_panel, "  Rock  ")
		self.rock_tabs.addTab(graph_panel, "  Graph  ")
		root.addWidget(self.rock_tabs, 1)

		self.import_button.clicked.connect(self._pick_import_file)
		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)
		self.system_picker.currentTextChanged.connect(self._sync_system_picker)
		self.graph_system_picker.currentTextChanged.connect(self._sync_system_picker)
		self.saturation_filter.textChanged.connect(self._sync_saturation_filter)
		self.graph_saturation_filter.textChanged.connect(self._sync_saturation_filter)
		self.graph_system_picker.setCurrentText(self.system_picker.currentText())

		# Keep legacy alias for external callers
		self.table_preview = self.wo_table

	def _make_control_label(self, text: str) -> QLabel:
		label = QLabel(text)
		label.setObjectName("pageControlLabel")
		return label

	def _sync_system_picker(self, text: str) -> None:
		for picker in (self.system_picker, self.graph_system_picker):
			if picker.currentText() == text:
				continue
			picker.blockSignals(True)
			picker.setCurrentText(text)
			picker.blockSignals(False)
		self._refresh_tables()

	def _sync_saturation_filter(self, text: str) -> None:
		for field in (self.saturation_filter, self.graph_saturation_filter):
			if field.text() == text:
				continue
			field.blockSignals(True)
			field.setText(text)
			field.blockSignals(False)
		self._refresh_tables()

	def _graph_series(self) -> list[dict[str, object]]:
		visible_sections = set(self._SYSTEM_OPTIONS.get(self.system_picker.currentText(), ("wo", "gas")))
		filter_text = self.saturation_filter.text().strip()
		series: list[dict[str, object]] = []
		for key, (label, sat_name) in self._GRAPH_META.items():
			system = "wo" if key in {"kro", "krw", "pcow"} else "gas"
			if system not in visible_sections:
				continue
			points = [(sat, value) for sat, value in self._rock_tables.get(key, []) if not filter_text or filter_text in f"{sat:.4f}"]
			if not points:
				continue
			series.append({
				"key": key,
				"label": label,
				"x_label": f"{sat_name} saturation",
				"points": points,
			})
		return series

	def _pick_import_file(self) -> None:
		path, _ = QFileDialog.getOpenFileName(
			self, "Import Rock-Fluid CSV/Excel", "",
			"Data Files (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)",
		)
		if path:
			self.importFileRequested.emit(path)

	def set_import_feedback(self, message: str, *, is_error: bool = False) -> None:
		self.import_feedback.setText(message)
		self.import_feedback.setVisible(bool(message.strip()))
		self.import_feedback.setProperty("feedbackKind", "error" if is_error else "ok")
		self.import_feedback.style().unpolish(self.import_feedback)
		self.import_feedback.style().polish(self.import_feedback)

	def _refresh_tables(self) -> None:
		filter_text = self.saturation_filter.text().strip()
		visible_sections = set(self._SYSTEM_OPTIONS.get(self.system_picker.currentText(), ("wo", "gas")))
		wo_rows = _fill_table(self.wo_table, self._rock_tables, [k for k, _ in self._WO_KEYS], filter_text)
		gas_rows = _fill_table(self.gas_table, self._rock_tables, [k for k, _ in self._GAS_KEYS], filter_text)
		self.wo_section.setVisible("wo" in visible_sections)
		self.gas_section.setVisible("gas" in visible_sections)
		if not self._rock_tables:
			self._empty_note.setVisible(True)
			self._empty_note.setText("Load the example rock-fluid dataset to inspect water-oil and gas-system tables.")
			self.rock_plot.set_series([])
			return
		if wo_rows == 0 and gas_rows == 0:
			self._empty_note.setVisible(True)
			self._empty_note.setText("No saturation rows match the current filter. Clear the filter to inspect the full tables.")
			self.rock_plot.set_series([])
			return
		self._empty_note.setVisible(False)
		self.rock_plot.set_series(self._graph_series())

	def set_project(self, project_config: ProjectConfig) -> None:
		tables = project_config.rock_tables
		self._rock_tables = tables
		if tables:
			self._status.setText(f"{len(tables)} tabel rock-fluid.")
			self._status.setProperty("chipKind", "ok")
		else:
			self._status.setText("Belum ada data.")
			self._status.setProperty("chipKind", "empty")
			self.import_feedback.setText("")
			self.import_feedback.setVisible(False)
		self._status.style().unpolish(self._status)
		self._status.style().polish(self._status)
		self._refresh_tables()

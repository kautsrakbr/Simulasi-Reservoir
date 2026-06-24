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


class _PVTMultiPlotWidget(QWidget):
	_SURFACE = QColor("#FFFFFF")
	_WORKSPACE = QColor("#F7F9FB")
	_SURFACE_ALT = QColor("#F1F4F8")
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
		"bo": QColor("#B7791F"),
		"bw": QColor("#2563A6"),
		"bg": QColor("#0F766E"),
		"mu_o": QColor("#A86A15"),
		"mu_w": QColor("#2E7DAE"),
		"mu_g": QColor("#5C6F91"),
		"rso": QColor("#A14F49"),
		"rsw": QColor("#2D6A4F"),
	}

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._rows: list[tuple[float, dict[str, float | None]]] = []
		self._series: list[tuple[str, str]] = []
		self._hit_points: list[dict[str, object]] = []
		self._hover_hit: dict[str, object] | None = None
		self._selected_hit: dict[str, object] | None = None
		self.setMouseTracking(True)
		self.setCursor(Qt.CursorShape.CrossCursor)
		self.setMinimumHeight(620)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	def set_data(self, rows: list[tuple[float, dict[str, float | None]]], series: list[tuple[str, str]]) -> None:
		self._rows = rows
		self._series = series
		self._hover_hit = None
		self._selected_hit = None
		self._update_canvas_height()
		self.update()

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

	def sizeHint(self) -> QSize:
		return QSize(980, self.minimumHeight())

	def _visible_series_count(self) -> int:
		if not self._rows or not self._series:
			return 0
		count = 0
		for key, _ in self._series:
			if any(values.get(key) is not None for _, values in self._rows):
				count += 1
		return count

	def _update_canvas_height(self) -> None:
		count = self._visible_series_count()
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

		if not self._rows or not self._series:
			p.setPen(self._MUTED)
			p.setFont(QFont("Segoe UI", 9))
			p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Belum ada data PVT untuk diplot")
			p.end()
			return

		visible_series = []
		self._hit_points = []
		for key, label in self._series:
			points = [(pressure, values.get(key)) for pressure, values in self._rows if values.get(key) is not None]
			if len(points) >= 1:
				visible_series.append((key, label, points))

		if not visible_series:
			p.setPen(self._MUTED)
			p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Tidak ada property yang cocok dengan filter")
			p.end()
			return

		count = len(visible_series)
		cols = self._column_count(count)
		rows = (count + cols - 1) // cols
		outer = self.rect().adjusted(14, 12, -14, -14)
		gap = 22
		panel_w = (outer.width() - gap * (cols - 1)) / cols
		panel_h = (outer.height() - gap * (rows - 1)) / rows

		for idx, (key, label, points) in enumerate(visible_series):
			col = idx % cols
			row = idx // cols
			rect = QRectF(
				outer.left() + col * (panel_w + gap),
				outer.top() + row * (panel_h + gap),
				panel_w,
				panel_h,
			)
			self._draw_panel(p, rect, key, label, points)
		self._draw_interaction_overlay(p)
		p.end()

	def _draw_panel(self, p: QPainter, rect: QRectF, key: str, label: str, points: list[tuple[float, float | None]]) -> None:
		line = self._COLORS.get(key, QColor("#0F5C8E"))
		label_main, _, label_unit = label.replace("\n", " ").partition(" ")
		label_detail = label.replace("\n", " ").replace(label_main, "", 1).strip() or "Property"

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

		xs = [x for x, y in points if y is not None]
		ys = [float(y) for x, y in points if y is not None]
		if not xs or not ys:
			return
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

		plot_points = [(x, float(y), to_pt(x, float(y))) for x, y in points if y is not None]
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
		for pressure, value, pt in plot_points:
			p.drawEllipse(pt, 4.2, 4.2)
			self._hit_points.append({
				"point": pt,
				"plot": plot,
				"pressure": pressure,
				"value": value,
				"label": label.replace("\n", " "),
				"color": line,
			})

		self._draw_axis_labels(p, plot, xmin, xmax, ymin, ymax, "Pressure (psia)", x_fmt="{value:.0f}", x_suffix=" psi")
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

	def _draw_axis_labels(
		self,
		p: QPainter,
		plot: QRectF,
		xmin: float,
		xmax: float,
		ymin: float,
		ymax: float,
		x_label: str,
		*,
		x_fmt: str,
		x_suffix: str = "",
	) -> None:
		p.setFont(QFont("Segoe UI", 7))
		p.setPen(self._MUTED)
		for i in range(5):
			value = ymax - (ymax - ymin) * i / 4
			y = plot.top() + plot.height() * i / 4
			p.drawText(QRectF(plot.left() - 56, y - 7, 48, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:.3g}")
		for i in range(4):
			value = xmin + (xmax - xmin) * i / 3
			x = plot.left() + plot.width() * i / 3
			text = x_fmt.format(value=value) + x_suffix
			p.drawText(QRectF(x - 34, plot.bottom() + 6, 68, 14), Qt.AlignmentFlag.AlignCenter, text)
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
		label = str(hit.get("label", "PVT"))
		pressure = float(hit.get("pressure", 0.0))
		value = float(hit.get("value", 0.0))
		return (
			f"<div style='font-family:\"Segoe UI\"; font-weight:600;'>{label}</div>"
			f"<div style='font-family:\"Segoe UI\",sans-serif; font-size:8.5pt;'>"
			f"Pressure = {pressure:.2f} psia<br/>Nilai = {value:.6g}</div>"
		)


class PVTPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()
	importFileRequested = Signal(str)

	# (key in pvt_tables, column header)
	_COLS: list[tuple[str, str]] = [
		("bo",   "Bo\n(RB/STB)"),
		("bw",   "Bw\n(RB/STB)"),
		("bg",   "Bg\n(RB/Mscf)"),
		("mu_o", "μo\n(cp)"),
		("mu_w", "μw\n(cp)"),
		("mu_g", "μg\n(cp)"),
		("rso",  "Rso\n(scf/STB)"),
		("rsw",  "Rsw\n(scf/STB)"),
	]
	_COLUMN_GROUPS: dict[str, tuple[str, ...]] = {
		"All Properties": ("bo", "bw", "bg", "mu_o", "mu_w", "mu_g", "rso", "rsw"),
		"Volume Factors": ("bo", "bw", "bg"),
		"Viscosities": ("mu_o", "mu_w", "mu_g"),
		"Solution Gas": ("rso", "rsw"),
	}

	def __init__(self) -> None:
		super().__init__()
		self._row_snapshots: list[tuple[float, dict[str, float | None]]] = []
		root = QVBoxLayout(self)
		root.setSpacing(12)
		root.setContentsMargins(18, 16, 18, 18)

		# ── Header row ────────────────────────────────────────────────
		hdr = QHBoxLayout()
		hdr.setSpacing(12)
		title_block = QVBoxLayout()
		title_block.setSpacing(3)
		title = QLabel("PVT Properties")
		title.setObjectName("pageTitle")
		self._subtitle = QLabel("Review, import, and verify reservoir fluid-property tables before simulation.")
		self._subtitle.setObjectName("pageSubtitle")
		self._status = QLabel("Belum ada data.")
		self._status.setObjectName("pageStatusChip")
		self._status.hide()
		title_block.addWidget(title)
		title_block.addWidget(self._subtitle)
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
		self.load_button = QPushButton("Load Contoh PVT")
		self.load_button.setObjectName("pvtSecondaryButton")
		self.clear_button = QPushButton("Hapus PVT")
		self.clear_button.setObjectName("pvtDangerButton")
		for b in (self.import_button, self.load_button, self.clear_button):
			b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
			b.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_row.addWidget(self.import_button)
		btn_row.addWidget(self.load_button)
		btn_row.addWidget(self.clear_button)
		btn_row.addStretch()
		actions_root.addLayout(btn_row)

		# ── Feedback label ────────────────────────────────────────────
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
		table_root.setSpacing(6)
		table_header = QHBoxLayout()
		table_header.setSpacing(12)
		table_title = QLabel("PVT Table Preview")
		table_title.setObjectName("pageSectionTitle")
		table_header.addWidget(table_title)
		table_header.addStretch()
		table_root.addLayout(table_header)
		self._empty_note = QLabel("Import CSV/Excel or load the example dataset to populate the pressure-aligned matrix.")
		self._empty_note.setObjectName("pageEmptyNote")
		self._empty_note.setWordWrap(True)
		table_root.addWidget(self._empty_note)

		controls_card = QFrame()
		controls_card.setObjectName("pageSubPanel")
		controls_row = QHBoxLayout(controls_card)
		controls_row.setContentsMargins(14, 12, 14, 12)
		controls_row.setSpacing(10)
		controls_row.addWidget(self._make_control_label("Property Focus"))
		self.group_picker = QComboBox()
		self.group_picker.setObjectName("pageCompactControl")
		self.group_picker.addItems(self._COLUMN_GROUPS.keys())
		controls_row.addWidget(self.group_picker)
		controls_row.addWidget(self._make_control_label("Pressure Filter"))
		self.pressure_filter = QLineEdit()
		self.pressure_filter.setObjectName("pageCompactField")
		self.pressure_filter.setPlaceholderText("e.g. 2500")
		controls_row.addWidget(self.pressure_filter)
		controls_row.addStretch()
		table_root.addWidget(controls_card)

		# ── Wide-format table ─────────────────────────────────────────
		col_count = 1 + len(self._COLS)
		self.table_preview = QTableWidget(0, col_count)
		self.table_preview.setObjectName("dataTable")
		hdrs = ["Pressure\n(psia)"] + [h for _, h in self._COLS]
		self.table_preview.setHorizontalHeaderLabels(hdrs)
		self.table_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table_preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table_preview.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table_preview.setAlternatingRowColors(True)
		self.table_preview.verticalHeader().setVisible(False)
		self.table_preview.setMinimumHeight(360)
		self.table_preview.setSortingEnabled(True)
		hh = self.table_preview.horizontalHeader()
		hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		for i in range(1, col_count):
			hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
		table_root.addWidget(self.table_preview)

		# ── Format hint ───────────────────────────────────────────────
		self.import_info = QLabel(
			"Format CSV/Excel — Long: kolom (table, pressure, value) | "
			"Wide: kolom (pressure, bo, bw, bg, mu_o, mu_w, mu_g, rso, rsw)"
		)
		self.import_info.setObjectName("pageHintLabel")
		self.import_info.setWordWrap(True)
		table_root.addWidget(self.import_info)

		graph_panel = QFrame()
		graph_panel.setObjectName("pageSectionPanel")
		graph_root = QVBoxLayout(graph_panel)
		graph_root.setContentsMargins(16, 14, 16, 16)
		graph_root.setSpacing(10)
		graph_header = QHBoxLayout()
		graph_title = QLabel("PVT Pressure Curves")
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
		graph_controls_row.addWidget(self._make_control_label("Property Focus"))
		self.graph_group_picker = QComboBox()
		self.graph_group_picker.setObjectName("pageCompactControl")
		self.graph_group_picker.addItems(self._COLUMN_GROUPS.keys())
		graph_controls_row.addWidget(self.graph_group_picker)
		graph_controls_row.addWidget(self._make_control_label("Pressure Filter"))
		self.graph_pressure_filter = QLineEdit()
		self.graph_pressure_filter.setObjectName("pageCompactField")
		self.graph_pressure_filter.setPlaceholderText("e.g. 2500")
		graph_controls_row.addWidget(self.graph_pressure_filter)
		graph_controls_row.addStretch()
		graph_root.addWidget(graph_controls)
		self.pvt_plot = _PVTMultiPlotWidget()
		self.pvt_plot.setObjectName("pvtPlotCanvas")
		plot_scroll = QScrollArea()
		plot_scroll.setObjectName("pvtPlotScroll")
		plot_scroll.setWidgetResizable(True)
		plot_scroll.setFrameShape(QFrame.Shape.NoFrame)
		plot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		plot_scroll.setWidget(self.pvt_plot)
		graph_root.addWidget(plot_scroll, 1)

		self.pvt_tabs = QTabWidget()
		self.pvt_tabs.setObjectName("subTabs")
		self.pvt_tabs.tabBar().setObjectName("subTabBar")
		self.pvt_tabs.tabBar().setExpanding(False)
		self.pvt_tabs.setDocumentMode(True)
		self.pvt_tabs.addTab(table_panel, "  PVT  ")
		self.pvt_tabs.addTab(graph_panel, "  Graph  ")
		root.addWidget(self.pvt_tabs, 1)

		self.import_button.clicked.connect(self._pick_import_file)
		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)
		self.group_picker.currentTextChanged.connect(self._sync_group_picker)
		self.graph_group_picker.currentTextChanged.connect(self._sync_group_picker)
		self.pressure_filter.textChanged.connect(self._sync_pressure_filter)
		self.graph_pressure_filter.textChanged.connect(self._sync_pressure_filter)
		self.graph_group_picker.setCurrentText(self.group_picker.currentText())

	def _make_control_label(self, text: str) -> QLabel:
		label = QLabel(text)
		label.setObjectName("pageControlLabel")
		return label

	def _sync_group_picker(self, text: str) -> None:
		for picker in (self.group_picker, self.graph_group_picker):
			if picker.currentText() == text:
				continue
			picker.blockSignals(True)
			picker.setCurrentText(text)
			picker.blockSignals(False)
		self._apply_column_visibility()

	def _sync_pressure_filter(self, text: str) -> None:
		for field in (self.pressure_filter, self.graph_pressure_filter):
			if field.text() == text:
				continue
			field.blockSignals(True)
			field.setText(text)
			field.blockSignals(False)
		self._refresh_table()

	def _pick_import_file(self) -> None:
		path, _ = QFileDialog.getOpenFileName(
			self, "Import PVT CSV/Excel", "",
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

	def set_project(self, project_config: ProjectConfig) -> None:
		tables = project_config.pvt_tables
		if tables:
			n_pts = max((len(v) for v in tables.values()), default=0)
			total_samples = sum(len(v) for v in tables.values())
			self._status.setText(f"{len(tables)} tbl  ·  {n_pts} lvl  ·  {total_samples} pts")
			self._status.setProperty("chipKind", "ok")
		else:
			self._status.setText("No data")
			self._status.setProperty("chipKind", "empty")
			self.import_feedback.setText("")
			self.import_feedback.setVisible(False)
		self._status.style().unpolish(self._status)
		self._status.style().polish(self._status)

		if not tables:
			self._row_snapshots = []
			self._empty_note.setVisible(True)
			self.table_preview.setRowCount(0)
			self._refresh_plot([])
			return

		# Collect all unique pressures across all tables (in order)
		col_keys = [k for k, _ in self._COLS]
		seen: set[float] = set()
		pressures: list[float] = []
		for k in col_keys:
			for p, _ in tables.get(k, []):
				if p not in seen:
					seen.add(p)
					pressures.append(p)
		for k, pts in tables.items():
			if k not in col_keys:
				for p, _ in pts:
					if p not in seen:
						seen.add(p)
						pressures.append(p)
		pressures.sort()
		self._empty_note.setVisible(False)

		lookup: dict[str, dict[float, float]] = {
			k: {p: v for p, v in pts} for k, pts in tables.items()
		}
		self._row_snapshots = [
			(
				pres,
				{key: lookup.get(key, {}).get(pres) for key in col_keys},
			)
			for pres in pressures
		]
		self._refresh_table()

	def _filtered_rows(self) -> list[tuple[float, dict[str, float | None]]]:
		filter_text = self.pressure_filter.text().strip()
		rows: list[tuple[float, dict[str, float | None]]] = []
		for pressure, values in self._row_snapshots:
			if filter_text and filter_text not in f"{pressure:.2f}":
				continue
			rows.append((pressure, values))
		return rows

	def _visible_series(self) -> list[tuple[str, str]]:
		visible_keys = set(self._COLUMN_GROUPS.get(self.group_picker.currentText(), self._COLUMN_GROUPS["All Properties"]))
		return [(key, label) for key, label in self._COLS if key in visible_keys]

	def _refresh_plot(self, rows: list[tuple[float, dict[str, float | None]]] | None = None) -> None:
		if rows is None:
			rows = self._filtered_rows()
		self.pvt_plot.set_data(rows, self._visible_series())

	def _refresh_table(self) -> None:
		default_empty_note = "Import CSV/Excel or load the example dataset to populate the pressure-aligned matrix."
		rows = self._filtered_rows()

		self.table_preview.setSortingEnabled(False)
		self.table_preview.clearSelection()
		self.table_preview.setRowCount(len(rows))
		col_keys = [k for k, _ in self._COLS]
		for r, (pres, values) in enumerate(rows):
			_cell(self.table_preview, r, 0, f"{pres:.2f}")
			for c, key in enumerate(col_keys, 1):
				val = values.get(key)
				_cell(self.table_preview, r, c, f"{val:.6g}" if val is not None else "—")
		self.table_preview.resizeRowsToContents()
		self.table_preview.setSortingEnabled(True)
		self._empty_note.setText(default_empty_note)
		self._empty_note.setVisible(not self._row_snapshots)
		self._apply_column_visibility()
		self._refresh_plot(rows)
		if rows:
			self.table_preview.selectRow(0)
		else:
			self._empty_note.setVisible(True)
			self._empty_note.setText("No pressure rows match the current filter. Clear the filter to inspect the full dataset.")

	def _apply_column_visibility(self) -> None:
		visible_keys = set(self._COLUMN_GROUPS.get(self.group_picker.currentText(), self._COLUMN_GROUPS["All Properties"]))
		for col_index, (key, _) in enumerate(self._COLS, start=1):
			hide = key not in visible_keys
			self.table_preview.setColumnHidden(col_index, hide)
		if hasattr(self, "pvt_plot"):
			self._refresh_plot()

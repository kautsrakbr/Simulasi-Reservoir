from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
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
	QTabWidget,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult, TimeStepResult
from modules.results_service import get_run_summary


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

	_COLOR_LINE  = QColor("#5b9ec9")
	_COLOR_OK    = QColor("#1e6d4e")
	_COLOR_FAIL  = QColor("#b64842")
	_COLOR_GRID  = QColor("#e8eef4")
	_COLOR_AXIS  = QColor("#7a96aa")
	_COLOR_BG    = QColor("#f8fbfd")
	_COLOR_PLOT  = QColor("#ffffff")
	_COLOR_BORDER = QColor("#dce6ef")

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


# ── ResultsPage ───────────────────────────────────────────────────────────────

class ResultsPage(QWidget):
	"""Results viewer — grid symmetry checker, residual bars, convergence log."""

	goToRunRequested = Signal()

	def __init__(self) -> None:
		super().__init__()
		self._nx = 2
		self._ny = 1
		self._run_result: RunResult | None = None
		self._active_run_result: RunResult | None = None  # alias for retry table
		self._selected_cell: int | None = None
		self._well_cell: int = 1
		self._cell_btns: dict[int, QPushButton] = {}

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
		self._tabs.addTab(self._build_grid_tab(),     "  Grid & Simetri  ")
		self._tabs.addTab(self._build_residual_tab(), "  Residual  ")
		self._tabs.addTab(self._build_conv_tab(),     "  Konvergensi  ")
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
						item.setBackground(QColor("#dff6dd"))
					elif sv == "abort-min-dt":
						item.setBackground(QColor("#f8d7da"))
					else:
						item.setBackground(QColor("#fff3cd"))
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
			self._badge.setText("Belum ada run")
			self._badge.setProperty("status", "empty")
			_repolish(self._badge)
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
		self._refresh_cell_colors()
		if self._selected_cell is not None:
			self._update_sel_card()
			self._update_sym_card()

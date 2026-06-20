from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QFrame,
	QGraphicsDropShadowEffect,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QPushButton,
	QSizePolicy,
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
	t.setAlternatingRowColors(True)
	t.verticalHeader().setVisible(False)
	hh = t.horizontalHeader()
	hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
	for i in range(1, len(headers)):
		hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
	shadow = QGraphicsDropShadowEffect(t)
	shadow.setBlurRadius(16)
	shadow.setColor(QColor(15, 23, 42, 20))
	shadow.setOffset(0, 3)
	t.setGraphicsEffect(shadow)
	return t


def _fill_table(
	table: QTableWidget,
	rock_tables: dict[str, list[tuple[float, float]]],
	col_keys: list[str],
) -> None:
	seen: set[float] = set()
	sats: list[float] = []
	for k in col_keys:
		for s, _ in rock_tables.get(k, []):
			if s not in seen:
				seen.add(s)
				sats.append(s)
	sats.sort()
	lookup = {k: {s: v for s, v in rock_tables.get(k, [])} for k in col_keys}
	table.setRowCount(len(sats))
	for r, sat in enumerate(sats):
		_cell(table, r, 0, f"{sat:.4f}")
		for c, k in enumerate(col_keys, 1):
			val = lookup[k].get(sat)
			_cell(table, r, c, f"{val:.6g}" if val is not None else "—")
	table.resizeRowsToContents()


class RockPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()

	# Water-Oil columns: index = Sw
	_WO_KEYS = [("kro", "Kro"), ("krw", "Krw"), ("pcow", "Pc_ow\n(psia)")]
	# Gas columns: index = Sg
	_GAS_KEYS = [("krg", "Krg"), ("pcgw", "Pc_gw\n(psia)")]

	def __init__(self) -> None:
		super().__init__()
		root = QVBoxLayout(self)
		root.setSpacing(8)
		root.setContentsMargins(14, 14, 14, 14)

		# ── Header row ────────────────────────────────────────────────
		hdr = QHBoxLayout()
		title = QLabel("Rock & Fluid Properties")
		title.setObjectName("pageTitle")
		self._status = QLabel("Belum ada data.")
		self._status.setObjectName("pageStatusChip")
		hdr.addWidget(title)
		hdr.addStretch()
		hdr.addWidget(self._status)
		root.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		root.addWidget(sep)

		# ── Button row ────────────────────────────────────────────────
		btn_row = QHBoxLayout()
		btn_row.setSpacing(8)
		self.load_button = QPushButton("Load Contoh Rock-Fluid")
		self.load_button.setObjectName("pvtSecondaryButton")
		self.clear_button = QPushButton("Hapus Rock-Fluid")
		self.clear_button.setObjectName("pvtDangerButton")
		for b in (self.load_button, self.clear_button):
			b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
			b.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_row.addWidget(self.load_button)
		btn_row.addStretch()
		btn_row.addWidget(self.clear_button)
		root.addLayout(btn_row)

		# ── Water-Oil table ───────────────────────────────────────────
		wo_label = QLabel("Water-Oil System")
		wo_label.setObjectName("tableGroupLabel")
		root.addWidget(wo_label)
		self.wo_table = _make_table(["Sw"] + [h for _, h in self._WO_KEYS])
		root.addWidget(self.wo_table, stretch=1)

		# ── Gas table ─────────────────────────────────────────────────
		gas_label = QLabel("Gas System")
		gas_label.setObjectName("tableGroupLabel")
		root.addWidget(gas_label)
		self.gas_table = _make_table(["Sg"] + [h for _, h in self._GAS_KEYS])
		root.addWidget(self.gas_table, stretch=1)

		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)

		# Keep legacy alias for external callers
		self.table_preview = self.wo_table

	def set_project(self, project_config: ProjectConfig) -> None:
		tables = project_config.rock_tables
		if tables:
			self._status.setText(f"{len(tables)} tabel rock-fluid.")
			self._status.setProperty("chipKind", "ok")
		else:
			self._status.setText("Belum ada data.")
			self._status.setProperty("chipKind", "empty")
		self._status.style().unpolish(self._status)
		self._status.style().polish(self._status)

		_fill_table(self.wo_table, tables, [k for k, _ in self._WO_KEYS])
		_fill_table(self.gas_table, tables, [k for k, _ in self._GAS_KEYS])

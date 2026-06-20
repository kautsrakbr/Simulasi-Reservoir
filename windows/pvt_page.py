from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QFileDialog,
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


class PVTPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()
	importFileRequested = Signal(str)

	# (key in pvt_tables, column header)
	_COLS: list[tuple[str, str]] = [
		("bo",   "Bo\n(RB/STB)"),
		("bw",   "Bw\n(RB/STB)"),
		("bg",   "Bg\n(RB/Mscf)"),
		("mu_o", "μ_o\n(cp)"),
		("mu_w", "μ_w\n(cp)"),
		("mu_g", "μ_g\n(cp)"),
		("rso",  "Rs_o\n(scf/STB)"),
		("rsw",  "Rs_w\n(scf/STB)"),
	]

	def __init__(self) -> None:
		super().__init__()
		root = QVBoxLayout(self)
		root.setSpacing(8)
		root.setContentsMargins(14, 14, 14, 14)

		# ── Header row ────────────────────────────────────────────────
		hdr = QHBoxLayout()
		title = QLabel("PVT Properties")
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
		self.import_button = QPushButton("⬆  Import CSV / Excel")
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
		btn_row.addStretch()
		btn_row.addWidget(self.clear_button)
		root.addLayout(btn_row)

		# ── Feedback label ────────────────────────────────────────────
		self.import_feedback = QLabel("")
		self.import_feedback.setObjectName("pageFeedback")
		self.import_feedback.setWordWrap(True)
		root.addWidget(self.import_feedback)

		# ── Wide-format table ─────────────────────────────────────────
		col_count = 1 + len(self._COLS)
		self.table_preview = QTableWidget(0, col_count)
		self.table_preview.setObjectName("dataTable")
		hdrs = ["Pressure\n(psia)"] + [h for _, h in self._COLS]
		self.table_preview.setHorizontalHeaderLabels(hdrs)
		self.table_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table_preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table_preview.setAlternatingRowColors(True)
		self.table_preview.verticalHeader().setVisible(False)
		hh = self.table_preview.horizontalHeader()
		hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		for i in range(1, col_count):
			hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
		table_shadow = QGraphicsDropShadowEffect(self.table_preview)
		table_shadow.setBlurRadius(16)
		table_shadow.setColor(QColor(15, 23, 42, 20))
		table_shadow.setOffset(0, 3)
		self.table_preview.setGraphicsEffect(table_shadow)
		root.addWidget(self.table_preview, stretch=1)

		# ── Format hint ───────────────────────────────────────────────
		self.import_info = QLabel(
			"Format CSV/Excel — Long: kolom (table, pressure, value) | "
			"Wide: kolom (pressure, bo, bw, bg, mu_o, mu_w, mu_g, rso, rsw)"
		)
		self.import_info.setObjectName("pageHintLabel")
		self.import_info.setWordWrap(True)
		root.addWidget(self.import_info)

		self.import_button.clicked.connect(self._pick_import_file)
		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)

	def _pick_import_file(self) -> None:
		path, _ = QFileDialog.getOpenFileName(
			self, "Import PVT CSV/Excel", "",
			"Data Files (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)",
		)
		if path:
			self.importFileRequested.emit(path)

	def set_import_feedback(self, message: str, *, is_error: bool = False) -> None:
		self.import_feedback.setText(message)
		self.import_feedback.setProperty("feedbackKind", "error" if is_error else "ok")
		self.import_feedback.style().unpolish(self.import_feedback)
		self.import_feedback.style().polish(self.import_feedback)

	def set_project(self, project_config: ProjectConfig) -> None:
		tables = project_config.pvt_tables
		if tables:
			n_pts = max((len(v) for v in tables.values()), default=0)
			self._status.setText(f"{len(tables)} tabel  ·  {n_pts} titik tekanan")
			self._status.setProperty("chipKind", "ok")
		else:
			self._status.setText("Belum ada data.")
			self._status.setProperty("chipKind", "empty")
			self.import_feedback.setText("")
		self._status.style().unpolish(self._status)
		self._status.style().polish(self._status)

		if not tables:
			self.table_preview.setRowCount(0)
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

		lookup: dict[str, dict[float, float]] = {
			k: {p: v for p, v in pts} for k, pts in tables.items()
		}

		self.table_preview.setRowCount(len(pressures))
		for r, pres in enumerate(pressures):
			_cell(self.table_preview, r, 0, f"{pres:.2f}")
			for c, key in enumerate(col_keys, 1):
				val = lookup.get(key, {}).get(pres)
				_cell(self.table_preview, r, c, f"{val:.6g}" if val is not None else "—")
		self.table_preview.resizeRowsToContents()

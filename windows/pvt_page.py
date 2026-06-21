from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
		root.addWidget(table_panel)
		root.addStretch(1)

		self.import_button.clicked.connect(self._pick_import_file)
		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)
		self.group_picker.currentTextChanged.connect(self._apply_column_visibility)
		self.pressure_filter.textChanged.connect(lambda _: self._refresh_table())

	def _make_control_label(self, text: str) -> QLabel:
		label = QLabel(text)
		label.setObjectName("pageControlLabel")
		return label

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

	def _refresh_table(self) -> None:
		default_empty_note = "Import CSV/Excel or load the example dataset to populate the pressure-aligned matrix."
		filter_text = self.pressure_filter.text().strip()
		rows: list[tuple[float, dict[str, float | None]]] = []
		for pressure, values in self._row_snapshots:
			if filter_text and filter_text not in f"{pressure:.2f}":
				continue
			rows.append((pressure, values))

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

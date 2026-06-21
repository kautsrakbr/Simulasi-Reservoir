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
	QScrollArea,
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


class RockPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()
	importFileRequested = Signal(str)

	# Water-Oil columns: index = Sw
	_WO_KEYS = [("kro", "Kro"), ("krw", "Krw"), ("pcow", "Pc_ow\n(psia)")]
	# Gas columns: index = Sg
	_GAS_KEYS = [("krg", "Krg"), ("pcgw", "Pc_gw\n(psia)")]
	_SYSTEM_OPTIONS = {
		"All Systems": ("wo", "gas"),
		"Water-Oil": ("wo",),
		"Gas": ("gas",),
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
		root.addWidget(table_panel)
		root.addStretch(1)

		self.import_button.clicked.connect(self._pick_import_file)
		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)
		self.system_picker.currentTextChanged.connect(self._refresh_tables)
		self.saturation_filter.textChanged.connect(lambda _: self._refresh_tables())

		# Keep legacy alias for external callers
		self.table_preview = self.wo_table

	def _make_control_label(self, text: str) -> QLabel:
		label = QLabel(text)
		label.setObjectName("pageControlLabel")
		return label

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
			return
		if wo_rows == 0 and gas_rows == 0:
			self._empty_note.setVisible(True)
			self._empty_note.setText("No saturation rows match the current filter. Clear the filter to inspect the full tables.")
			return
		self._empty_note.setVisible(False)

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

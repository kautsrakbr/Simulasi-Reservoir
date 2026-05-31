from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QAbstractItemView,
	QFrame,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


class RockPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setContentsMargins(24, 20, 24, 20)
		outer.setSpacing(12)

		# ── Header ──
		hdr = QHBoxLayout()
		title = QLabel("Rock-Fluid Tables")
		title.setObjectName("pageTitle")
		self.status_label = QLabel("No tables loaded")
		self.status_label.setObjectName("metaLabel")
		self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		hdr.addWidget(title)
		hdr.addWidget(self.status_label, 1)
		outer.addLayout(hdr)

		# ── Action bar ──
		action_bar = QHBoxLayout()
		self.load_button = QPushButton("Load Example Rock-Fluid")
		self.clear_button = QPushButton("Clear Rock-Fluid")
		self.clear_button.setObjectName("btnSecondary")
		action_bar.addWidget(self.load_button)
		action_bar.addWidget(self.clear_button)
		action_bar.addStretch(1)
		outer.addLayout(action_bar)

		# ── Table preview card ──
		card = QFrame()
		card.setObjectName("card")
		card_layout = QVBoxLayout(card)
		card_layout.setContentsMargins(0, 0, 0, 0)
		card_layout.setSpacing(0)
		tbl_hdr = QWidget()
		tbl_hdr.setFixedHeight(36)
		tbl_hdr_box = QHBoxLayout(tbl_hdr)
		tbl_hdr_box.setContentsMargins(14, 0, 14, 0)
		tbl_hdr_box.addWidget(QLabel("Rock-Fluid Data (Relperm & Capillary Pressure)"))
		card_layout.addWidget(tbl_hdr)
		self.table_preview = QTableWidget()
		self.table_preview.setColumnCount(3)
		self.table_preview.setHorizontalHeaderLabels(["Table", "Saturation", "Value"])
		self.table_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
		self.table_preview.setAlternatingRowColors(True)
		self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.table_preview.verticalHeader().setVisible(False)
		card_layout.addWidget(self.table_preview, 1)
		outer.addWidget(card, 1)

		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)

	def set_project(self, project_config: ProjectConfig) -> None:
		n = len(project_config.rock_tables)
		rows = sum(len(pts) for pts in project_config.rock_tables.values())
		self.status_label.setText(f"{n} tables  |  {rows} data points" if n > 0 else "No tables loaded")
		self.table_preview.setRowCount(rows)
		row_idx = 0
		for tbl_name, points in project_config.rock_tables.items():
			for saturation, value in points:
				self.table_preview.setItem(row_idx, 0, QTableWidgetItem(tbl_name))
				self.table_preview.setItem(row_idx, 1, QTableWidgetItem(f"{saturation:.4f}"))
				self.table_preview.setItem(row_idx, 2, QTableWidgetItem(f"{value:.6f}"))
				row_idx += 1

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from engine.domain.project import ProjectConfig


class RockPage(QWidget):
	loadExampleRequested = Signal()
	clearRequested = Signal()

	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Rock Page")
		self.status_label = QLabel()
		self.table_preview = QTableWidget(self)
		self.table_preview.setColumnCount(3)
		self.table_preview.setHorizontalHeaderLabels(["Table", "Input", "Value"])
		self.load_button = QPushButton("Load Example Rock-Fluid", self)
		self.clear_button = QPushButton("Clear Rock-Fluid", self)

		layout.addWidget(title)
		layout.addWidget(self.status_label)
		layout.addWidget(self.table_preview)
		layout.addWidget(self.load_button)
		layout.addWidget(self.clear_button)

		self.load_button.clicked.connect(self.loadExampleRequested)
		self.clear_button.clicked.connect(self.clearRequested)

	def set_project(self, project_config: ProjectConfig) -> None:
		self.status_label.setText(f"Loaded rock tables: {len(project_config.rock_tables)}")
		rows = sum(len(points) for points in project_config.rock_tables.values())
		self.table_preview.setRowCount(rows)
		row_index = 0
		for table_name, points in project_config.rock_tables.items():
			for saturation, value in points:
				self.table_preview.setItem(row_index, 0, QTableWidgetItem(table_name))
				self.table_preview.setItem(row_index, 1, QTableWidgetItem(f"{saturation:.4f}"))
				self.table_preview.setItem(row_index, 2, QTableWidgetItem(f"{value:.6f}"))
				row_index += 1

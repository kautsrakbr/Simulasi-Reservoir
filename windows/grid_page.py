from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class GridPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Grid Page")
		description = QLabel(
			"Halaman ini akan menampung input dimensi grid, properti cell, dan validasi geometri model."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

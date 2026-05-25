from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class InitialPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Initial Page")
		description = QLabel(
			"Halaman ini akan menangani pressure awal, saturasi awal, dan kondisi start time step."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

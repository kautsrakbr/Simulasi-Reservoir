from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RockPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Rock Page")
		description = QLabel(
			"Halaman ini akan memuat relative permeability, capillary pressure, dan data rock-fluid lain."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

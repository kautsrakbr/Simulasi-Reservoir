from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ModelPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Model Page")
		description = QLabel(
			"Halaman ini akan menjadi tempat metadata project dan pengaturan model utama."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

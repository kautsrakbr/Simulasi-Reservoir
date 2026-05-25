from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResultsPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Results Page")
		description = QLabel(
			"Halaman ini akan menampilkan summary, trend, map, dan table hasil simulasi."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

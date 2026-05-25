from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RunPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Run Page")
		description = QLabel(
			"Halaman ini akan mengelola tombol run, progress runtime, log, dan kontrol eksekusi solver."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

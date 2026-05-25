from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PVTPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("PVT Page")
		description = QLabel(
			"Halaman ini akan menampung tabel PVT dan validasi properti fluida sebelum run."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

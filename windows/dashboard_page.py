from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DashboardPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Dashboard")
		description = QLabel(
			"Halaman ini akan menampilkan readiness model, status validasi, dan ringkasan run."
		)
		description.setWordWrap(True)

		layout.addWidget(title)
		layout.addWidget(description)

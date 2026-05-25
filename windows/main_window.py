from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from windows.dashboard_page import DashboardPage
from windows.grid_page import GridPage
from windows.initial_page import InitialPage
from windows.model_page import ModelPage
from windows.pvt_page import PVTPage
from windows.results_page import ResultsPage
from windows.rock_page import RockPage
from windows.run_page import RunPage

class MainWindow(QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("Simulasi Reservoir")
		self.resize(1440, 900)

		central_widget = QWidget(self)
		central_layout = QHBoxLayout(central_widget)

		self.navigation = QListWidget(central_widget)
		self.navigation.setMinimumWidth(220)

		self.page_stack = QStackedWidget(central_widget)
		self._add_pages()

		central_layout.addWidget(self.navigation)
		central_layout.addWidget(self.page_stack, 1)

		self.setCentralWidget(central_widget)

		self.navigation.currentRowChanged.connect(self.page_stack.setCurrentIndex)
		self.navigation.setCurrentRow(0)

	def _add_pages(self) -> None:
		pages = [
			("Dashboard", DashboardPage()),
			("Model", ModelPage()),
			("Grid", GridPage()),
			("PVT", PVTPage()),
			("Rock", RockPage()),
			("Initial", InitialPage()),
			("Run", RunPage()),
			("Results", ResultsPage()),
		]

		for title, page in pages:
			self.navigation.addItem(title)
			self.page_stack.addWidget(page)

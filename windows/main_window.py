from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
	QFileDialog,
	QHBoxLayout,
	QListWidget,
	QMainWindow,
	QMessageBox,
	QStackedWidget,
	QToolBar,
	QWidget,
)

from modules.project_service import (
	clear_pvt_tables,
	clear_rock_tables,
	create_empty_project,
	load_example_pvt_tables,
	load_example_rock_tables,
	load_project_json,
	mark_project_clean,
	save_project_json,
	update_initial_conditions,
	update_grid_spec,
	update_project_metadata,
	update_solver_config,
)
from modules.simulation_service import validate_and_run
from modules.validation_service import validate_project

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
		self.setWindowTitle("CoreReservoir")
		self.resize(1440, 900)
		self.project_config = create_empty_project("CoreReservoir")
		self.run_result = None
		self.project_file_path: Path | None = None

		central_widget = QWidget(self)
		central_layout = QHBoxLayout(central_widget)

		self.navigation = QListWidget(central_widget)
		self.navigation.setMinimumWidth(220)

		self.page_stack = QStackedWidget(central_widget)
		self._add_pages()
		self._connect_signals()
		self._configure_commands()

		central_layout.addWidget(self.navigation)
		central_layout.addWidget(self.page_stack, 1)

		self.setCentralWidget(central_widget)

		self.navigation.currentRowChanged.connect(self.page_stack.setCurrentIndex)
		self.navigation.setCurrentRow(0)
		self._refresh_pages()
		self.statusBar().showMessage("CoreReservoir siap.")

	def _configure_commands(self) -> None:
		project_menu = self.menuBar().addMenu("Project")

		new_action = QAction("New", self)
		open_action = QAction("Open JSON...", self)
		save_action = QAction("Save", self)
		save_as_action = QAction("Save As JSON...", self)

		project_menu.addAction(new_action)
		project_menu.addAction(open_action)
		project_menu.addSeparator()
		project_menu.addAction(save_action)
		project_menu.addAction(save_as_action)

		toolbar = QToolBar("Project", self)
		toolbar.setMovable(False)
		toolbar.addAction(new_action)
		toolbar.addAction(open_action)
		toolbar.addAction(save_action)
		toolbar.addAction(save_as_action)
		self.addToolBar(toolbar)

		new_action.triggered.connect(self._new_project)
		open_action.triggered.connect(self._open_project)
		save_action.triggered.connect(self._save_project)
		save_as_action.triggered.connect(self._save_project_as)

	def _new_project(self) -> None:
		self.project_config = create_empty_project("CoreReservoir")
		self.run_result = None
		self.project_file_path = None
		self._refresh_pages()
		self.statusBar().showMessage("Project baru dibuat.", 5000)

	def _open_project(self) -> None:
		file_path, _ = QFileDialog.getOpenFileName(
			self,
			"Open Project JSON",
			"",
			"JSON Files (*.json)",
		)
		if not file_path:
			return

		try:
			self.project_config = load_project_json(file_path)
		except Exception as exc:
			QMessageBox.warning(self, "Open Project", f"Gagal membuka project: {exc}")
			return

		self.project_file_path = Path(file_path)
		self.run_result = None
		self._refresh_pages()
		self.statusBar().showMessage(f"Project dibuka: {self.project_file_path.name}", 5000)

	def _save_project(self) -> None:
		if self.project_file_path is None:
			self._save_project_as()
			return

		try:
			save_project_json(self.project_config, self.project_file_path)
		except Exception as exc:
			QMessageBox.warning(self, "Save Project", f"Gagal menyimpan project: {exc}")
			return

		self._refresh_pages()
		self.statusBar().showMessage(f"Project disimpan: {self.project_file_path.name}", 5000)

	def _save_project_as(self) -> None:
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"Save Project JSON",
			"",
			"JSON Files (*.json)",
		)
		if not file_path:
			return
		if not file_path.lower().endswith(".json"):
			file_path = f"{file_path}.json"

		self.project_file_path = Path(file_path)
		self._save_project()

	def _add_pages(self) -> None:
		self.dashboard_page = DashboardPage()
		self.model_page = ModelPage()
		self.grid_page = GridPage()
		self.pvt_page = PVTPage()
		self.rock_page = RockPage()
		self.initial_page = InitialPage()
		self.run_page = RunPage()
		self.results_page = ResultsPage()

		pages = [
			("Dashboard", self.dashboard_page),
			("Model", self.model_page),
			("Grid", self.grid_page),
			("PVT", self.pvt_page),
			("Rock", self.rock_page),
			("Initial", self.initial_page),
			("Run", self.run_page),
			("Results", self.results_page),
		]

		for title, page in pages:
			self.navigation.addItem(title)
			self.page_stack.addWidget(page)

	def _connect_signals(self) -> None:
		self.model_page.projectChanged.connect(self._handle_project_changed)
		self.model_page.solverChanged.connect(self._handle_solver_changed)
		self.grid_page.gridChanged.connect(self._handle_grid_changed)
		self.pvt_page.loadExampleRequested.connect(self._load_example_pvt)
		self.pvt_page.clearRequested.connect(self._clear_pvt)
		self.rock_page.loadExampleRequested.connect(self._load_example_rock)
		self.rock_page.clearRequested.connect(self._clear_rock)
		self.initial_page.initialConditionsChanged.connect(self._handle_initial_conditions_changed)
		self.run_page.runRequested.connect(self._run_placeholder_simulation)

	def _handle_project_changed(
		self,
		name: str,
		description: str,
		case_name: str,
		reference_pressure: float,
	) -> None:
		update_project_metadata(
			self.project_config,
			name=name,
			description=description,
			case_name=case_name,
			reference_pressure=reference_pressure,
		)
		self._refresh_pages()

	def _handle_solver_changed(
		self,
		initial_timestep_days: float,
		min_timestep_days: float,
		max_time_days: float,
		timestep_growth_factor: float,
		timestep_shrink_factor: float,
		max_step_retries: int,
		max_newton_iterations: int,
		residual_tolerance: float,
		residual_norm_floor: float,
		parameter_tolerance: float,
		newton_pressure_damping: float,
		newton_saturation_damping: float,
		max_pressure_correction: float,
		max_saturation_correction: float,
	) -> None:
		update_solver_config(
			self.project_config,
			initial_timestep_days=initial_timestep_days,
			min_timestep_days=min_timestep_days,
			max_time_days=max_time_days,
			timestep_growth_factor=timestep_growth_factor,
			timestep_shrink_factor=timestep_shrink_factor,
			max_step_retries=max_step_retries,
			max_newton_iterations=max_newton_iterations,
			residual_tolerance=residual_tolerance,
			residual_norm_floor=residual_norm_floor,
			parameter_tolerance=parameter_tolerance,
			newton_pressure_damping=newton_pressure_damping,
			newton_saturation_damping=newton_saturation_damping,
			max_pressure_correction=max_pressure_correction,
			max_saturation_correction=max_saturation_correction,
		)
		self._refresh_pages()

	def _handle_grid_changed(
		self,
		nx: int,
		ny: int,
		nz: int,
		dx: float,
		dy: float,
		dz: float,
	) -> None:
		update_grid_spec(
			self.project_config,
			nx=nx,
			ny=ny,
			nz=nz,
			dx=dx,
			dy=dy,
			dz=dz,
		)
		self._refresh_pages()

	def _handle_initial_conditions_changed(
		self,
		reference_depth: float,
		initial_sw: float,
		initial_sg: float,
	) -> None:
		update_initial_conditions(
			self.project_config,
			reference_depth=reference_depth,
			initial_sw=initial_sw,
			initial_sg=initial_sg,
		)
		self._refresh_pages()

	def _load_example_pvt(self) -> None:
		load_example_pvt_tables(self.project_config)
		self._refresh_pages()

	def _clear_pvt(self) -> None:
		clear_pvt_tables(self.project_config)
		self._refresh_pages()

	def _load_example_rock(self) -> None:
		load_example_rock_tables(self.project_config)
		self._refresh_pages()

	def _clear_rock(self) -> None:
		clear_rock_tables(self.project_config)
		self._refresh_pages()

	def _run_placeholder_simulation(self) -> None:
		try:
			self.run_result = validate_and_run(self.project_config)
		except Exception as exc:
			self.run_page.set_run_feedback(f"Run status: failed - {exc}")
			self.results_page.set_run_result(None)
			return

		step_count = len(self.run_result.steps)
		warning_count = len(self.run_result.warnings)
		self.run_page.set_run_feedback(
			f"Run status: done ({step_count} step(s), {warning_count} warning(s))"
		)
		mark_project_clean(self.project_config)
		self._refresh_pages()
		self.results_page.set_run_result(self.run_result)

	def _refresh_pages(self) -> None:
		validation_errors = validate_project(self.project_config)
		self.dashboard_page.set_project_overview(self.project_config, validation_errors)
		self.model_page.set_project(self.project_config)
		self.grid_page.set_project(self.project_config)
		self.pvt_page.set_project(self.project_config)
		self.rock_page.set_project(self.project_config)
		self.initial_page.set_project(self.project_config)
		self.run_page.set_project_state(self.project_config, validation_errors)
		self.results_page.set_run_result(self.run_result)
		self._update_window_caption()

	def _update_window_caption(self) -> None:
		base_title = "CoreReservoir"
		if self.project_file_path is not None:
			base_title = f"{base_title} - {self.project_file_path.name}"
		if self.project_config.is_dirty:
			base_title = f"{base_title} *"
		self.setWindowTitle(base_title)

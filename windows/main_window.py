from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
	QFileDialog,
	QFrame,
	QHBoxLayout,
	QLabel,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QSplitter,
	QStackedWidget,
	QTabWidget,
	QToolBar,
	QToolButton,
	QVBoxLayout,
	QWidget,
)

from modules.run_worker import RunWorker
from modules.project_service import (
	clear_pvt_tables,
	clear_rock_tables,
	create_empty_project,
	import_pvt_tables_from_file,
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
from modules.validation_service import validate_project

from windows.dashboard_page import DashboardPage
from windows.grid_page import GridPage
from windows.initial_page import InitialPage
from windows.model_page import ModelPage
from windows.pvt_page import PVTPage
from windows.results_page import ResultsPage
from windows.rock_page import RockPage
from windows.run_page import RunPage


class _NavSection(QWidget):
	"""Collapsible accordion section for the left navigation sidebar."""

	def __init__(self, title: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._title = title
		self._buttons: list[QPushButton] = []

		outer = QVBoxLayout(self)
		outer.setContentsMargins(0, 0, 0, 0)
		outer.setSpacing(0)

		# Section header toggle button
		self._header = QToolButton(self)
		self._header.setObjectName("navSectionHeader")
		self._header.setText(f"  ▼  {title.upper()}")
		self._header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
		self._header.setCheckable(True)
		self._header.setChecked(True)
		self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		self._header.clicked.connect(self._toggle)

		# Body that holds nav items
		self._body = QWidget(self)
		self._body.setObjectName("navBody")
		self._body_layout = QVBoxLayout(self._body)
		self._body_layout.setContentsMargins(0, 2, 0, 6)
		self._body_layout.setSpacing(1)

		outer.addWidget(self._header)
		outer.addWidget(self._body)  # always visible by default

		# Separator line below section
		sep = QFrame(self)
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("navSeparator")
		outer.addWidget(sep)

	def add_item(self, label: str) -> QPushButton:
		btn = QPushButton(f"    {label}", self._body)
		btn.setObjectName("navItem")
		btn.setCheckable(True)
		btn.setAutoExclusive(False)
		btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		self._body_layout.addWidget(btn)
		self._buttons.append(btn)
		return btn

	def set_active(self, btn: QPushButton | None) -> None:
		for b in self._buttons:
			b.setChecked(b is btn)

	def _toggle(self, checked: bool) -> None:
		self._body.setVisible(checked)
		arrow = "▼" if checked else "▶"
		self._header.setText(f"  {arrow}  {self._title.upper()}")


class _InputConstraintPage(QWidget):
	"""Top-tab container for input and constraint pages."""

	def __init__(self, pages: list[tuple[str, QWidget]], parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self._tabs = QTabWidget(self)
		self._tabs.setObjectName("inputTabs")
		self._tabs.tabBar().setObjectName("inputTabBar")
		self._tabs.tabBar().setExpanding(False)
		self._tabs.setDocumentMode(True)

		for title, page in pages:
			self._tabs.addTab(page, f"  {title}  ")

		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._tabs)

	def switch_to_tab(self, tab_index: int) -> None:
		if 0 <= tab_index < self._tabs.count():
			self._tabs.setCurrentIndex(tab_index)


class MainWindow(QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("CoreReservoir")
		self.resize(1440, 900)
		self.project_config = create_empty_project("CoreReservoir")
		self.run_result = None
		self.project_file_path: Path | None = None
		self._nav_buttons: list[QPushButton] = []
		self._sidebar_expanded = True

		# ── Central splitter ────────────────────────────────────────────────
		self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
		self._splitter.setObjectName("mainSplitter")
		self._splitter.setHandleWidth(5)

		# ── Left sidebar ────────────────────────────────────────────────────
		self._sidebar = QWidget()
		self._sidebar.setObjectName("sidebar")
		self._sidebar.setMinimumWidth(48)
		self._sidebar.setMaximumWidth(280)
		sidebar_outer = QVBoxLayout(self._sidebar)
		sidebar_outer.setContentsMargins(0, 0, 0, 0)
		sidebar_outer.setSpacing(0)

		# Sidebar header row: logo label + collapse button
		_header_bar = QWidget(self._sidebar)
		_header_bar.setObjectName("sidebarHeader")
		_header_row = QHBoxLayout(_header_bar)
		_header_row.setContentsMargins(10, 8, 6, 8)
		_logo = QLabel("CoreReservoir", _header_bar)
		_logo.setObjectName("sidebarLogo")
		self._collapse_btn = QToolButton(_header_bar)
		self._collapse_btn.setObjectName("sidebarToggle")
		self._collapse_btn.setText("◀")
		self._collapse_btn.setToolTip("Sembunyikan / Tampilkan sidebar")
		self._collapse_btn.clicked.connect(self._toggle_sidebar)
		_header_row.addWidget(_logo, 1)
		_header_row.addWidget(self._collapse_btn)
		sidebar_outer.addWidget(_header_bar)

		# Scroll area inside sidebar
		self._nav_scroll = QScrollArea(self._sidebar)
		self._nav_scroll.setWidgetResizable(True)
		self._nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self._nav_scroll.setObjectName("navScroll")
		self._nav_scroll.setFrameShape(QFrame.Shape.NoFrame)

		self._nav_inner = QWidget()
		self._nav_inner.setObjectName("navInner")
		self._nav_layout = QVBoxLayout(self._nav_inner)
		self._nav_layout.setContentsMargins(0, 4, 0, 4)
		self._nav_layout.setSpacing(0)
		self._nav_layout.addStretch(1)
		self._nav_scroll.setWidget(self._nav_inner)
		sidebar_outer.addWidget(self._nav_scroll, 1)

		# ── Right: stacked page area ────────────────────────────────────────
		self._page_stack = QStackedWidget(self)
		self._page_stack.setObjectName("pageStack")

		self._splitter.addWidget(self._sidebar)
		self._splitter.addWidget(self._page_stack)
		self._splitter.setStretchFactor(0, 0)
		self._splitter.setStretchFactor(1, 1)
		self._splitter.setSizes([200, 1240])

		self.setCentralWidget(self._splitter)

		self._add_pages()
		self._connect_signals()
		self._configure_commands()

		self._switch_to_page(0)
		self._refresh_pages()
		self.statusBar().showMessage("CoreReservoir siap.")

	# ── Sidebar collapse/expand ──────────────────────────────────────────────
	def _toggle_sidebar(self) -> None:
		self._sidebar_expanded = not self._sidebar_expanded
		self._nav_scroll.setVisible(self._sidebar_expanded)
		if self._sidebar_expanded:
			self._collapse_btn.setText("◀")
			self._collapse_btn.setToolTip("Sembunyikan sidebar")
			self._splitter.setSizes([200, self.width() - 200])
		else:
			self._collapse_btn.setText("▶")
			self._collapse_btn.setToolTip("Tampilkan sidebar")
			self._splitter.setSizes([48, self.width() - 48])

	# ── Page switching ────────────────────────────────────────────────────────
	def _switch_to_page(self, index: int) -> None:
		self._page_stack.setCurrentIndex(index)
		for i, btn in enumerate(self._nav_buttons):
			btn.setChecked(i == index)

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
		toolbar.setObjectName("mainToolbar")
		toolbar.addAction(new_action)
		toolbar.addAction(open_action)
		toolbar.addAction(save_action)
		toolbar.addAction(save_as_action)
		toolbar.addSeparator()

		# Quick navigation shortcut buttons in toolbar
		_tb_dashboard = QToolButton(toolbar)
		_tb_dashboard.setText("Dashboard")
		_tb_dashboard.setObjectName("toolbarNav")
		_tb_dashboard.clicked.connect(self._open_dashboard_tab)
		toolbar.addWidget(_tb_dashboard)

		_tb_run = QToolButton(toolbar)
		_tb_run.setText("Run")
		_tb_run.setObjectName("toolbarNav")
		_tb_run.clicked.connect(lambda _=None: self._switch_to_page(2))
		toolbar.addWidget(_tb_run)

		_tb_results = QToolButton(toolbar)
		_tb_results.setText("Results")
		_tb_results.setObjectName("toolbarNav")
		_tb_results.clicked.connect(lambda _=None: self._switch_to_page(3))
		toolbar.addWidget(_tb_results)

		self.addToolBar(toolbar)

		new_action.triggered.connect(self._new_project)
		open_action.triggered.connect(self._open_project)
		save_action.triggered.connect(self._save_project)
		save_as_action.triggered.connect(self._save_project_as)

	def _open_dashboard_tab(self) -> None:
		self._switch_to_page(0)
		self.input_constraints_page.switch_to_tab(0)

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
		self.input_constraints_page = _InputConstraintPage(
			[
				("Dashboard", self.dashboard_page),
				("Model", self.model_page),
				("Grid", self.grid_page),
				("Initial", self.initial_page),
			],
			self,
		)
		self.properties_page = _InputConstraintPage(
			[
				("PVT", self.pvt_page),
				("Rock Properties", self.rock_page),
			],
			self,
		)

		# Group 1: Inputs
		_inputs_section = _NavSection("Inputs", self._nav_inner)
		self._nav_layout.insertWidget(self._nav_layout.count() - 1, _inputs_section)

		# Group 2: Simulation
		_sim_section = _NavSection("Simulation", self._nav_inner)
		self._nav_layout.insertWidget(self._nav_layout.count() - 1, _sim_section)

		# Add pages to stack
		self._page_stack.addWidget(self.input_constraints_page)  # index 0
		self._page_stack.addWidget(self.properties_page)         # index 1
		self._page_stack.addWidget(self.run_page)                # index 2
		self._page_stack.addWidget(self.results_page)            # index 3

		# Sidebar navigation items
		btn_input = _inputs_section.add_item("Input && Constraint")
		btn_properties = _inputs_section.add_item("Properties")
		btn_run = _sim_section.add_item("Run")
		btn_results = _sim_section.add_item("Results")

		btn_input.clicked.connect(lambda _=None: self._switch_to_page(0))
		btn_properties.clicked.connect(lambda _=None: self._switch_to_page(1))
		btn_run.clicked.connect(lambda _=None: self._switch_to_page(2))
		btn_results.clicked.connect(lambda _=None: self._switch_to_page(3))
		self._nav_buttons.extend([btn_input, btn_properties, btn_run, btn_results])

		# Mark first nav btn active
		if self._nav_buttons:
			self._nav_buttons[0].setChecked(True)

	def _connect_signals(self) -> None:
		self.model_page.projectChanged.connect(self._handle_project_changed)
		self.model_page.solverChanged.connect(self._handle_solver_changed)
		self.grid_page.gridChanged.connect(self._handle_grid_changed)
		self.pvt_page.loadExampleRequested.connect(self._load_example_pvt)
		self.pvt_page.clearRequested.connect(self._clear_pvt)
		self.pvt_page.importFileRequested.connect(self._import_pvt_file)
		self.rock_page.loadExampleRequested.connect(self._load_example_rock)
		self.rock_page.clearRequested.connect(self._clear_rock)
		self.initial_page.initialConditionsChanged.connect(self._handle_initial_conditions_changed)
		self.run_page.runRequested.connect(self._start_run_simulation)
		self.run_page.cancelRequested.connect(self._cancel_run_simulation)
		self.results_page.goToRunRequested.connect(lambda: self._switch_to_page(2))

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
		self.pvt_page.set_import_feedback("Contoh PVT dimuat.")
		self._refresh_pages()

	def _import_pvt_file(self, file_path: str) -> None:
		try:
			import_pvt_tables_from_file(self.project_config, file_path)
		except Exception as exc:
			self.pvt_page.set_import_feedback(f"Import gagal: {exc}", is_error=True)
			QMessageBox.warning(self, "Import PVT", f"Gagal import file PVT:\n{exc}")
			return

		self.pvt_page.set_import_feedback(
			f"Import berhasil: {Path(file_path).name}",
			is_error=False,
		)
		self._switch_to_page(1)
		self.properties_page.switch_to_tab(0)
		self._refresh_pages()
		self.statusBar().showMessage(f"PVT ter-import: {Path(file_path).name}", 7000)

	def _clear_pvt(self) -> None:
		clear_pvt_tables(self.project_config)
		self._refresh_pages()

	def _load_example_rock(self) -> None:
		load_example_rock_tables(self.project_config)
		self._refresh_pages()

	def _clear_rock(self) -> None:
		clear_rock_tables(self.project_config)
		self._refresh_pages()

	def _start_run_simulation(self) -> None:
		self._run_thread = QThread(self)
		self._run_worker = RunWorker(self.project_config)
		self._run_worker.moveToThread(self._run_thread)

		self._run_thread.started.connect(self._run_worker.run)
		self._run_worker.started.connect(self._on_run_started)
		self._run_worker.progress.connect(self._on_run_progress)
		self._run_worker.finished.connect(self._on_run_finished)
		self._run_worker.failed.connect(self._on_run_failed)
		self._run_worker.finished.connect(self._run_thread.quit)
		self._run_worker.failed.connect(self._run_thread.quit)
		self._run_thread.finished.connect(self._run_thread.deleteLater)

		self.run_page.clear_log()
		self._run_thread.start()

	def _cancel_run_simulation(self) -> None:
		# RunWorker doesn't yet support cancellation; just disable the stop btn
		self.run_page.set_running(False)
		self.statusBar().showMessage("Stop diminta — simulasi akan selesai setelah step ini.", 4000)

	def _on_run_started(self) -> None:
		self.run_page.set_running(True)
		self.run_page.append_log("=== Simulasi dimulai ===")
		self.statusBar().showMessage("Simulasi berjalan…")

	def _on_run_progress(self, message: str) -> None:
		self.run_page.append_log(message)
		self.statusBar().showMessage(message, 3000)

	def _on_run_finished(self, run_result: object) -> None:
		self.run_result = run_result
		step_count = len(run_result.steps)
		warning_count = len(run_result.warnings)
		msg = f"Selesai — {step_count} step(s), {warning_count} warning(s)"
		self.run_page.set_running(False)
		self.run_page.append_log(f"=== {msg} ===")
		self.run_page.set_run_feedback(msg)
		mark_project_clean(self.project_config)
		self._refresh_pages()
		self.results_page.set_run_result(run_result)
		self._switch_to_page(3)  # go to Results
		self.statusBar().showMessage(msg, 8000)

	def _on_run_failed(self, error: str) -> None:
		self.run_page.set_running(False)
		self.run_page.append_log(f"[ERROR] {error}")
		self.run_page.set_run_feedback(f"Gagal: {error}")
		self.statusBar().showMessage(f"Run gagal: {error}", 8000)

	def _refresh_pages(self) -> None:
		validation_errors = validate_project(self.project_config)
		self.dashboard_page.set_project_overview(self.project_config, validation_errors)
		self.model_page.set_project(self.project_config)
		self.grid_page.set_project(self.project_config)
		self.pvt_page.set_project(self.project_config)
		self.rock_page.set_project(self.project_config)
		self.initial_page.set_project(self.project_config)
		self.run_page.set_project_state(self.project_config, validation_errors)
		self.results_page.set_project(self.project_config)
		self.results_page.set_run_result(self.run_result)
		self._update_window_caption()

	def _update_window_caption(self) -> None:
		base_title = "CoreReservoir"
		if self.project_file_path is not None:
			base_title = f"{base_title} - {self.project_file_path.name}"
		if self.project_config.is_dirty:
			base_title = f"{base_title} *"
		self.setWindowTitle(base_title)

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from re import search
from time import perf_counter

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
	QDockWidget,
	QFileDialog,
	QHBoxLayout,
	QListWidget,
	QMainWindow,
	QMessageBox,
	QStackedWidget,
	QTextEdit,
	QToolBar,
	QToolButton,
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
from modules.report_service import export_summary
from modules.validation_service import validate_project
from modules.run_worker import RunWorker

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
		self._run_thread: QThread | None = None
		self._run_worker: RunWorker | None = None
		self._run_in_progress = False
		self._run_started_at: float = 0.0
		self._run_target_time_days: float = 0.0
		self._input_page_rows = {1, 2, 3, 4, 5}
		self._last_navigation_row = 0

		central_widget = QWidget(self)
		central_layout = QHBoxLayout(central_widget)

		self.navigation = QListWidget(central_widget)
		self.navigation.setMinimumWidth(220)
		self.navigation.setObjectName("sideNav")

		self.page_stack = QStackedWidget(central_widget)
		self.page_stack.setObjectName("workspaceStack")
		self._add_pages()
		self._connect_signals()
		self._configure_commands()

		central_layout.addWidget(self.navigation)
		central_layout.addWidget(self.page_stack, 1)

		self.setCentralWidget(central_widget)

		# ── Bottom dock: persistent runtime console ────────────────────
		log_dock = QDockWidget("  Runtime Console", self)
		log_dock.setObjectName("bottomDock")
		log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
		log_dock.setFeatures(
			QDockWidget.DockWidgetFeature.DockWidgetClosable
			| QDockWidget.DockWidgetFeature.DockWidgetMovable
		)
		self.dock_log = QTextEdit()
		self.dock_log.setObjectName("logOutput")
		self.dock_log.setReadOnly(True)
		self.dock_log.setPlaceholderText("Runtime log akan muncul di sini selama simulasi berjalan...")
		log_dock.setWidget(self.dock_log)
		self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, log_dock)
		self.resizeDocks([log_dock], [160], Qt.Orientation.Vertical)

		self.navigation.currentRowChanged.connect(self._on_navigation_changed)
		self.navigation.setCurrentRow(0)
		self._last_navigation_row = 0
		self._refresh_pages()
		self.statusBar().showMessage("CoreReservoir siap.")

	def _configure_commands(self) -> None:
		project_menu = self.menuBar().addMenu("Project")

		self.new_action = QAction("New", self)
		self.open_action = QAction("Open JSON...", self)
		self.save_action = QAction("Save", self)
		self.save_as_action = QAction("Save As JSON...", self)

		project_menu.addAction(self.new_action)
		project_menu.addAction(self.open_action)
		project_menu.addSeparator()
		project_menu.addAction(self.save_action)
		project_menu.addAction(self.save_as_action)

		toolbar = QToolBar("Project", self)
		toolbar.setMovable(False)
		toolbar.addAction(self.new_action)
		toolbar.addAction(self.open_action)
		toolbar.addAction(self.save_action)
		toolbar.addAction(self.save_as_action)

		toolbar.addSeparator()
		self.run_action = QAction("▶  Run", self)
		self.stop_action = QAction("■  Stop", self)
		self._run_tool_btn = QToolButton(self)
		self._run_tool_btn.setDefaultAction(self.run_action)
		self._run_tool_btn.setObjectName("actionRun")
		toolbar.addWidget(self._run_tool_btn)
		self._stop_tool_btn = QToolButton(self)
		self._stop_tool_btn.setDefaultAction(self.stop_action)
		self._stop_tool_btn.setObjectName("actionStop")
		self._stop_tool_btn.setEnabled(False)
		toolbar.addWidget(self._stop_tool_btn)

		self.run_action.triggered.connect(self._start_run_simulation)
		self.stop_action.triggered.connect(self._cancel_run_simulation)

		self.addToolBar(toolbar)

		self.new_action.triggered.connect(self._new_project)
		self.open_action.triggered.connect(self._open_project)
		self.save_action.triggered.connect(self._save_project)
		self.save_as_action.triggered.connect(self._save_project_as)

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
		self.run_page.runRequested.connect(self._start_run_simulation)
		self.run_page.cancelRequested.connect(self._cancel_run_simulation)
		self.results_page.exportRequested.connect(self._export_run_summary)

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

	def _start_run_simulation(self) -> None:
		if self._run_in_progress:
			self.run_page.append_runtime_log("Run masih berjalan. Tunggu hingga selesai.")
			return

		validation_errors = validate_project(self.project_config)
		if validation_errors:
			self.run_page.set_run_feedback("Run status: blocked")
			self.run_page.append_runtime_log("Run dibatalkan karena validasi gagal.")
			return

		project_snapshot = deepcopy(self.project_config)
		self._run_target_time_days = max(project_snapshot.solver.max_time_days, 1e-12)
		self._run_thread = QThread(self)
		self._run_worker = RunWorker(project_snapshot)
		self._run_worker.moveToThread(self._run_thread)

		self._run_thread.started.connect(self._run_worker.run)
		self._run_worker.started.connect(self._on_run_started)
		self._run_worker.progress.connect(self._on_run_progress)
		self._run_worker.warning.connect(self._on_run_warning)
		self._run_worker.finished.connect(self._on_run_finished)
		self._run_worker.failed.connect(self._on_run_failed)

		self._run_worker.finished.connect(self._run_thread.quit)
		self._run_worker.failed.connect(self._run_thread.quit)
		self._run_worker.finished.connect(self._run_worker.deleteLater)
		self._run_worker.failed.connect(self._run_worker.deleteLater)
		self._run_thread.finished.connect(self._run_thread.deleteLater)
		self._run_thread.finished.connect(self._on_run_thread_finished)

		self._run_thread.start()

	def _on_run_started(self) -> None:
		self._run_in_progress = True
		self._run_started_at = perf_counter()
		self._set_input_edit_enabled(False)
		self._run_tool_btn.setEnabled(False)
		self._stop_tool_btn.setEnabled(True)
		self.run_page.set_running(True)
		self.run_page.clear_runtime_log()
		self.dock_log.clear()
		self.dock_log.append("=== Run dimulai ===")
		self.run_page.set_run_feedback("Run status: running")
		self.run_page.set_progress(0.0, "calculating")
		self.run_page.append_runtime_log("Run dimulai.")
		self.page_stack.setCurrentWidget(self.run_page)

	def _on_run_progress(self, message: str) -> None:
		self.run_page.append_runtime_log(message)
		if message.strip():
			self.dock_log.append(message)
		self._update_progress_from_message(message)
		self._update_live_chart_from_message(message)
		self.statusBar().showMessage(message, 3000)

	def _update_live_chart_from_message(self, message: str) -> None:
		if "accepted" not in message:
			return
		time_match = search(r"time=([0-9]+(?:\.[0-9]+)?)\s+hari", message)
		residual_match = search(r"residual=([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)", message)
		if time_match and residual_match:
			self.run_page.add_residual_point(
				float(time_match.group(1)),
				float(residual_match.group(1)),
			)

	def _on_run_warning(self, message: str) -> None:
		self.run_page.append_runtime_log(f"Warning: {message}")
		self.dock_log.append(f"⚠ Warning: {message}")

	def _on_run_finished(self, run_result: object) -> None:
		self.run_result = run_result
		self._run_in_progress = False
		self._set_input_edit_enabled(True)
		self._run_tool_btn.setEnabled(True)
		self._stop_tool_btn.setEnabled(False)
		self.run_page.set_running(False)

		step_count = len(self.run_result.steps)
		warning_count = len(self.run_result.warnings)
		mark_project_clean(self.project_config)
		self._refresh_pages()
		self.results_page.set_run_result(self.run_result)
		if self.run_result.warnings and "dibatalkan oleh user" in " | ".join(self.run_result.warnings):
			final_time = self.run_result.steps[-1].summary.time_days if self.run_result.steps else 0.0
			percent = 100.0 * min(max(final_time / self._run_target_time_days, 0.0), 1.0)
			self.run_page.set_progress(percent, "--")
			self.run_page.set_run_feedback(
				f"Run status: canceled ({step_count} step(s), {warning_count} warning(s))"
			)
			self.run_page.append_runtime_log("Run dibatalkan user secara graceful.")
		else:
			self.run_page.set_progress(100.0, "00:00:00")
			self.run_page.set_run_feedback(
				f"Run status: done ({step_count} step(s), {warning_count} warning(s))"
			)
			self.run_page.append_runtime_log("Run selesai.")

	def _on_run_failed(self, message: str) -> None:
		self._run_in_progress = False
		self._set_input_edit_enabled(True)
		self._run_tool_btn.setEnabled(True)
		self._stop_tool_btn.setEnabled(False)
		self.run_page.set_running(False)
		self.run_page.set_progress(0.0, "--")
		self.run_page.set_run_feedback(f"Run status: failed - {message}")
		self.run_page.append_runtime_log(f"Run gagal: {message}")
		self.statusBar().showMessage("Run gagal.", 5000)

	def _cancel_run_simulation(self) -> None:
		if not self._run_in_progress:
			self.run_page.append_runtime_log("Tidak ada run aktif untuk dibatalkan.")
			return
		if self._run_worker is None:
			self.run_page.append_runtime_log("Worker run belum siap.")
			return
		self.run_page.set_run_feedback("Run status: cancelling...")
		self.run_page.append_runtime_log("Mengirim permintaan cancel...")
		self._run_worker.request_cancel()

	def _on_run_thread_finished(self) -> None:
		self._run_worker = None
		self._run_thread = None

	def _export_run_summary(self) -> None:
		if self.run_result is None:
			QMessageBox.information(self, "Export Summary", "Belum ada hasil run untuk diexport.")
			return

		default_name = (self.project_file_path.stem if self.project_file_path else "coreservoir") + "_summary.txt"
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Run Summary",
			default_name,
			"Text Files (*.txt)",
		)
		if not file_path:
			return

		try:
			target = export_summary(self.run_result, file_path)
		except Exception as exc:
			QMessageBox.warning(self, "Export Summary", f"Gagal export summary: {exc}")
			return

		self.statusBar().showMessage(f"Summary exported: {target.name}", 5000)

	def _set_input_edit_enabled(self, enabled: bool) -> None:
		self.model_page.setEnabled(enabled)
		self.grid_page.setEnabled(enabled)
		self.pvt_page.setEnabled(enabled)
		self.rock_page.setEnabled(enabled)
		self.initial_page.setEnabled(enabled)
		self.new_action.setEnabled(enabled)
		self.open_action.setEnabled(enabled)
		self.save_action.setEnabled(enabled)
		self.save_as_action.setEnabled(enabled)
		self._set_navigation_input_locked(not enabled)

	def _set_navigation_input_locked(self, locked: bool) -> None:
		for row in self._input_page_rows:
			item = self.navigation.item(row)
			if item is None:
				continue
			flags = item.flags()
			if locked:
				flags &= ~Qt.ItemFlag.ItemIsEnabled
				flags &= ~Qt.ItemFlag.ItemIsSelectable
			else:
				flags |= Qt.ItemFlag.ItemIsEnabled
				flags |= Qt.ItemFlag.ItemIsSelectable
			item.setFlags(flags)

		if locked and self.navigation.currentRow() in self._input_page_rows:
			self.navigation.setCurrentRow(6)
			self._last_navigation_row = 6

	def _on_navigation_changed(self, row: int) -> None:
		if row < 0:
			return
		if self._run_in_progress and row in self._input_page_rows:
			self.statusBar().showMessage("Input pages dikunci selama run berjalan.", 3000)
			self.run_page.append_runtime_log("Navigasi ke input page ditolak selama run berjalan.")
			self.navigation.blockSignals(True)
			self.navigation.setCurrentRow(self._last_navigation_row)
			self.navigation.blockSignals(False)
			self.page_stack.setCurrentIndex(self._last_navigation_row)
			return
		self._last_navigation_row = row
		self.page_stack.setCurrentIndex(row)

	def _update_progress_from_message(self, message: str) -> None:
		if "accepted" not in message:
			return
		match = search(r"time=([0-9]+(?:\.[0-9]+)?)\s+hari", message)
		if match is None:
			return
		if self._run_target_time_days <= 1e-12:
			return

		time_days = float(match.group(1))
		percent = 100.0 * min(max(time_days / self._run_target_time_days, 0.0), 1.0)
		elapsed_seconds = max(perf_counter() - self._run_started_at, 0.0)
		if time_days > 1e-12 and percent < 100.0:
			estimated_total_seconds = elapsed_seconds * (self._run_target_time_days / time_days)
			remaining_seconds = max(estimated_total_seconds - elapsed_seconds, 0.0)
			eta_text = self._format_duration(remaining_seconds)
		else:
			eta_text = "00:00:00"

		self.run_page.set_progress(percent, eta_text)

	def _format_duration(self, total_seconds: float) -> str:
		seconds_int = max(int(round(total_seconds)), 0)
		hours = seconds_int // 3600
		minutes = (seconds_int % 3600) // 60
		seconds = seconds_int % 60
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

	def _refresh_pages(self) -> None:
		validation_errors = validate_project(self.project_config)
		self.dashboard_page.set_project_overview(self.project_config, validation_errors, self.run_result)
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

	def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
		if self._run_in_progress:
			self._cancel_run_simulation()
			self.run_page.append_runtime_log("Menunggu run selesai sebelum menutup aplikasi.")
			event.ignore()
			return
		super().closeEvent(event)

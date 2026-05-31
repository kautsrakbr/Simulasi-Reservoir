from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult


class _StatusCard(QFrame):
	"""Colored status card for dashboard readiness grid."""

	_OBJ = {"ok": "cardSuccess", "warning": "cardWarning", "error": "cardDanger", "neutral": "cardNeutral"}
	_DOT = {"ok": "#2D6A4F", "warning": "#A86A15", "error": "#B2413F", "neutral": "#5B6676"}

	def __init__(self, title: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("cardNeutral")
		self.setMinimumHeight(86)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

		vbox = QVBoxLayout(self)
		vbox.setContentsMargins(16, 12, 16, 12)
		vbox.setSpacing(4)

		header = QHBoxLayout()
		header.setSpacing(6)
		self._dot = QLabel("●")
		self._dot.setFixedWidth(14)
		self._dot.setStyleSheet("color: #5B6676; font-size: 11pt; background: transparent;")
		lbl = QLabel(title)
		lbl.setObjectName("cardTitle")
		header.addWidget(self._dot)
		header.addWidget(lbl, 1)
		vbox.addLayout(header)

		self._val = QLabel("—")
		self._val.setObjectName("metaValue")
		vbox.addWidget(self._val)

		self._detail = QLabel("")
		self._detail.setObjectName("metaLabel")
		self._detail.setWordWrap(True)
		vbox.addWidget(self._detail)

	def set_status(self, state: str, value: str, detail: str = "") -> None:
		self.setObjectName(self._OBJ.get(state, "cardNeutral"))
		self.style().polish(self)
		self._dot.setStyleSheet(
			f"color: {self._DOT.get(state, '#5B6676')}; font-size: 11pt; background: transparent;"
		)
		self._val.setText(value)
		self._detail.setText(detail)


class DashboardPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		root = QVBoxLayout(self)
		root.setContentsMargins(24, 20, 24, 20)
		root.setSpacing(16)

		# ── Page header ──
		hdr = QHBoxLayout()
		title = QLabel("Dashboard")
		title.setObjectName("pageTitle")
		self._chip = QLabel()
		self._chip.setObjectName("metaLabel")
		self._chip.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		hdr.addWidget(title)
		hdr.addWidget(self._chip, 1)
		root.addLayout(hdr)

		# ── Readiness card grid ──
		readiness_frame = QFrame(self)
		readiness_frame.setObjectName("card")
		rf_layout = QVBoxLayout(readiness_frame)
		rf_layout.setContentsMargins(16, 14, 16, 14)
		rf_layout.setSpacing(10)
		rf_title = QLabel("Model Readiness")
		rf_title.setObjectName("sectionTitle")
		rf_layout.addWidget(rf_title)

		grid = QGridLayout()
		grid.setSpacing(10)
		self._c_grid = _StatusCard("Grid")
		self._c_pvt = _StatusCard("PVT Tables")
		self._c_rock = _StatusCard("Rock-Fluid Tables")
		self._c_initial = _StatusCard("Initial Conditions")
		self._c_ready = _StatusCard("Model Ready")
		self._c_run = _StatusCard("Last Run")
		grid.addWidget(self._c_grid, 0, 0)
		grid.addWidget(self._c_pvt, 0, 1)
		grid.addWidget(self._c_rock, 0, 2)
		grid.addWidget(self._c_initial, 1, 0)
		grid.addWidget(self._c_ready, 1, 1)
		grid.addWidget(self._c_run, 1, 2)
		rf_layout.addLayout(grid)
		root.addWidget(readiness_frame)

		# ── Project info card ──
		info_frame = QFrame(self)
		info_frame.setObjectName("card")
		if_layout = QVBoxLayout(info_frame)
		if_layout.setContentsMargins(16, 14, 16, 14)
		if_layout.setSpacing(6)
		if_title = QLabel("Project Info")
		if_title.setObjectName("sectionTitle")
		if_layout.addWidget(if_title)
		self._l_project = QLabel()
		self._l_project.setObjectName("metaLabel")
		self._l_case = QLabel()
		self._l_case.setObjectName("metaLabel")
		self._l_grid = QLabel()
		self._l_grid.setObjectName("metaLabel")
		self._l_dirty = QLabel()
		self._l_dirty.setObjectName("metaLabel")
		for lbl in (self._l_project, self._l_case, self._l_grid, self._l_dirty):
			if_layout.addWidget(lbl)
		root.addWidget(info_frame)

		root.addStretch(1)

	# ── Public API ────────────────────────────────────────────────

	def set_project_overview(
		self,
		project_config: ProjectConfig,
		validation_errors: list[str],
		run_result: RunResult | None,
	) -> None:
		self._chip.setText(f"{project_config.name}  —  {project_config.run.case_name}")

		nx, ny, nz = project_config.grid_spec.nx, project_config.grid_spec.ny, project_config.grid_spec.nz
		cell_count = nx * ny * nz
		grid_str = f"{nx} \u00d7 {ny} \u00d7 {nz}"
		vol = cell_count * project_config.grid_spec.dx * project_config.grid_spec.dy * project_config.grid_spec.dz

		self._l_project.setText(f"Project:  {project_config.name}  |  {project_config.description}")
		self._l_case.setText(f"Case:  {project_config.run.case_name}")
		self._l_grid.setText(f"Grid:  {grid_str} = {cell_count} cells  |  Volume \u2248 {vol:,.0f} ft\u00b3")
		self._l_dirty.setText(
			"State:  \u26a0 Unsaved changes \u2014 run ulang disarankan" if project_config.is_dirty
			else "State:  \u2713 Synchronized"
		)

		# Grid card
		self._c_grid.set_status("ok", grid_str, f"{cell_count} active cells")

		# PVT card
		n_pvt = len(project_config.pvt_tables)
		pvt_err = [e for e in validation_errors if "pvt" in e.lower()]
		if n_pvt == 0:
			self._c_pvt.set_status("error", "Not loaded", "Load PVT tables to continue")
		elif pvt_err:
			self._c_pvt.set_status("warning", f"{n_pvt} tables", pvt_err[0])
		else:
			self._c_pvt.set_status("ok", f"{n_pvt} tables", "All PVT tables present")

		# Rock card
		n_rock = len(project_config.rock_tables)
		rock_err = [e for e in validation_errors if "rock" in e.lower() or "relperm" in e.lower()]
		if n_rock == 0:
			self._c_rock.set_status("error", "Not loaded", "Load rock-fluid tables to continue")
		elif rock_err:
			self._c_rock.set_status("warning", f"{n_rock} tables", rock_err[0])
		else:
			self._c_rock.set_status("ok", f"{n_rock} tables", "Relperm data present")

		# Initial conditions card
		sw = project_config.initial_conditions.initial_sw
		sg = project_config.initial_conditions.initial_sg
		so = max(0.0, 1.0 - sw - sg)
		ic_err = [e for e in validation_errors if "saturation" in e.lower() or "initial" in e.lower()]
		if (sw + sg) > 1.0:
			self._c_initial.set_status("error", "Invalid saturations", f"Sw+Sg = {sw+sg:.4f} > 1")
		elif ic_err:
			self._c_initial.set_status("warning", f"Sw={sw:.3f}  Sg={sg:.3f}", ic_err[0])
		else:
			self._c_initial.set_status("ok", f"Sw={sw:.3f}  Sg={sg:.3f}  So={so:.3f}", "Valid")

		# Model ready card
		if not validation_errors:
			self._c_ready.set_status("ok", "Ready to Run", "All checks passed")
		elif len(validation_errors) == 1:
			self._c_ready.set_status("warning", "1 issue", validation_errors[0])
		else:
			self._c_ready.set_status("error", f"{len(validation_errors)} issues", validation_errors[0])

		# Last run card
		if run_result is None or not run_result.steps:
			self._c_run.set_status("neutral", "No runs yet", "Run simulation to see results")
		else:
			last = run_result.steps[-1]
			warns = len(run_result.warnings)
			self._c_run.set_status(
				"warning" if warns > 0 else "ok",
				f"{len(run_result.steps)} steps  \u2014  {last.summary.time_days:.2f} days",
				f"Max residual: {last.summary.max_residual:.3e}  |  Warnings: {warns}",
			)

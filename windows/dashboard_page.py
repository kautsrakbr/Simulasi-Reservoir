from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QScrollArea,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


class _InfoCard(QFrame):
	"""A styled card widget with title and value rows."""

	_BORDER_COLORS = {
		"ok":      "#4caf7d",
		"warn":    "#e6a817",
		"error":   "#d9534f",
		"neutral": "#5b9ec9",
	}

	def __init__(self, title: str, state: str = "neutral", parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("dashCard")
		self._state = state
		self._apply_border(state)

		self._layout = QVBoxLayout(self)
		self._layout.setContentsMargins(14, 10, 14, 12)
		self._layout.setSpacing(6)

		self._title_label = QLabel(title.upper(), self)
		self._title_label.setObjectName("dashCardTitle")
		self._layout.addWidget(self._title_label)

		sep = QFrame(self)
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("dashCardSep")
		self._layout.addWidget(sep)

	def _apply_border(self, state: str) -> None:
		color = self._BORDER_COLORS.get(state, self._BORDER_COLORS["neutral"])
		self.setStyleSheet(
			f"QFrame#dashCard {{ "
			f"background: #ffffff; "
			f"border: 1px solid #dde6ee; "
			f"border-left: 4px solid {color}; "
			f"border-radius: 6px; }}"
		)

	def add_row(self, label: str, value: str, value_style: str = "") -> QLabel:
		row = QHBoxLayout()
		row.setContentsMargins(0, 0, 0, 0)
		lbl = QLabel(label, self)
		lbl.setObjectName("dashRowLabel")
		lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
		lbl.setMinimumWidth(110)
		val = QLabel(value, self)
		val.setObjectName("dashRowValue")
		val.setWordWrap(True)
		if value_style:
			val.setStyleSheet(value_style)
		row.addWidget(lbl)
		row.addWidget(val, 1)
		self._layout.addLayout(row)
		return val

	def set_state(self, state: str) -> None:
		if state != self._state:
			self._state = state
			self._apply_border(state)

	def clear_rows(self) -> None:
		while self._layout.count() > 2:  # keep title + sep
			item = self._layout.takeAt(2)
			if item.widget():
				item.widget().deleteLater()
			elif item.layout():
				# clear sub-layout items
				sub = item.layout()
				while sub.count():
					sub.takeAt(0)


class DashboardPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		# ── Header bar ──────────────────────────────────────────────────────
		self._header = QWidget(self)
		self._header.setObjectName("dashHeader")
		_header_row = QHBoxLayout(self._header)
		_header_row.setContentsMargins(20, 14, 20, 14)

		self._project_title = QLabel("CoreReservoir", self._header)
		self._project_title.setObjectName("dashTitle")

		self._status_badge = QLabel("READY", self._header)
		self._status_badge.setObjectName("dashBadgeReady")
		self._status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self._status_badge.setFixedWidth(90)

		_header_row.addWidget(self._project_title)
		_header_row.addStretch(1)
		_header_row.addWidget(self._status_badge)

		# ── Scroll area for cards ────────────────────────────────────────────
		scroll = QScrollArea(self)
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)

		content = QWidget()
		content.setObjectName("dashContent")
		grid = QGridLayout(content)
		grid.setContentsMargins(20, 16, 20, 20)
		grid.setHorizontalSpacing(16)
		grid.setVerticalSpacing(16)
		grid.setColumnStretch(0, 1)
		grid.setColumnStretch(1, 1)

		# Card: Project Info
		self._card_project = _InfoCard("Project Info", "neutral")
		self._val_name    = self._card_project.add_row("Name", "—")
		self._val_case    = self._card_project.add_row("Case", "—")
		self._val_state   = self._card_project.add_row("State", "—")

		# Card: Grid
		self._card_grid = _InfoCard("Grid", "neutral")
		self._val_dims   = self._card_grid.add_row("Dimensions", "—")
		self._val_cells  = self._card_grid.add_row("Cell Count", "—")

		# Card: Initial Conditions
		self._card_init = _InfoCard("Initial Conditions", "neutral")
		self._val_depth = self._card_init.add_row("Ref. Depth", "—")
		self._val_sw    = self._card_init.add_row("Sw (water)", "—")
		self._val_sg    = self._card_init.add_row("Sg (gas)", "—")
		self._val_so    = self._card_init.add_row("So (oil)", "—")

		# Card: Validation
		self._card_valid = _InfoCard("Validation", "neutral")
		self._val_valid  = self._card_valid.add_row("Status", "—")
		self._val_errors = self._card_valid.add_row("Issues", "—")

		grid.addWidget(self._card_project, 0, 0)
		grid.addWidget(self._card_grid,    0, 1)
		grid.addWidget(self._card_init,    1, 0)
		grid.addWidget(self._card_valid,   1, 1)
		grid.setRowStretch(2, 1)

		scroll.setWidget(content)

		# ── Root layout ──────────────────────────────────────────────────────
		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(scroll, 1)

	def set_project_overview(
		self,
		project_config: ProjectConfig,
		validation_errors: list[str],
		run_result=None,
	) -> None:
		# Header
		self._project_title.setText(project_config.name)

		# Project card
		self._val_name.setText(project_config.name)
		self._val_case.setText(project_config.run.case_name)
		state_text = "Dirty — perlu disimpan / dijalankan ulang" if project_config.is_dirty else "Clean"
		state_style = "color: #e6a817;" if project_config.is_dirty else "color: #4caf7d;"
		self._val_state.setText(state_text)
		self._val_state.setStyleSheet(state_style)
		self._card_project.set_state("warn" if project_config.is_dirty else "ok")

		# Grid card
		gs = project_config.grid_spec
		cells = gs.nx * gs.ny * gs.nz
		self._val_dims.setText(f"{gs.nx} × {gs.ny} × {gs.nz}")
		self._val_cells.setText(f"{cells:,} sel")
		self._card_grid.set_state("ok" if cells > 0 else "error")

		# Initial conditions card
		ic = project_config.initial_conditions
		so = max(0.0, 1.0 - ic.initial_sw - ic.initial_sg)
		self._val_depth.setText(f"{ic.reference_depth:,.2f} ft")
		self._val_sw.setText(f"{ic.initial_sw:.4f}")
		self._val_sg.setText(f"{ic.initial_sg:.4f}")
		self._val_so.setText(f"{so:.4f}")
		self._card_init.set_state("ok")

		# Validation card
		if validation_errors:
			self._val_valid.setText("Incomplete")
			self._val_valid.setStyleSheet("color: #d9534f; font-weight: bold;")
			self._val_errors.setText(" • " + "\n • ".join(validation_errors))
			self._val_errors.setStyleSheet("color: #d9534f;")
			self._card_valid.set_state("error")
			self._status_badge.setText("INCOMPLETE")
			self._status_badge.setObjectName("dashBadgeError")
		else:
			self._val_valid.setText("All checks passed")
			self._val_valid.setStyleSheet("color: #4caf7d; font-weight: bold;")
			self._val_errors.setText("—")
			self._val_errors.setStyleSheet("")
			self._card_valid.set_state("ok")
			self._status_badge.setText("READY")
			self._status_badge.setObjectName("dashBadgeReady")

		# Force badge style refresh
		self._status_badge.style().unpolish(self._status_badge)
		self._status_badge.style().polish(self._status_badge)


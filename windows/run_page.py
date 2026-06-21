from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QFrame,
	QHBoxLayout,
	QLabel,
	QProgressBar,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QTextEdit,
	QTableWidget,
	QTableWidgetItem,
	QHeaderView,
	QVBoxLayout,
	QWidget,
)
from PySide6.QtGui import QFont, QColor, QBrush

from engine.domain.project import ProjectConfig


class RunPage(QWidget):
	runRequested    = Signal()
	cancelRequested = Signal()

	def __init__(self) -> None:
		super().__init__()

		# ── Header Bar ───────────────────────────────────────────────────────
		self._header = QWidget(self)
		self._header.setObjectName("dashHeader")
		_hrow = QHBoxLayout(self._header)
		_hrow.setContentsMargins(20, 14, 20, 14)
		_hrow.setSpacing(10)

		_title = QLabel("Run Simulation", self._header)
		_title.setObjectName("dashTitle")

		self._run_btn = QPushButton("▶  Run", self._header)
		self._run_btn.setObjectName("runBtnPrimary")
		self._run_btn.setFixedWidth(110)
		self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)

		self._stop_btn = QPushButton("■  Stop", self._header)
		self._stop_btn.setObjectName("runBtnStop")
		self._stop_btn.setFixedWidth(110)
		self._stop_btn.setEnabled(False)
		self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)

		_hrow.addWidget(_title)
		_hrow.addStretch(1)
		_hrow.addWidget(self._run_btn)
		_hrow.addWidget(self._stop_btn)

		# ── Progress Bar ─────────────────────────────────────────────────────
		self._progress = QProgressBar(self)
		self._progress.setObjectName("runProgress")
		self._progress.setRange(0, 0)   # indeterminate by default
		self._progress.setFixedHeight(4)
		self._progress.setTextVisible(False)
		self._progress.setVisible(False)

		# ── Unified Control & Summary Panel (Technical summary table) ────────
		self.table_summary = QTableWidget(1, 4)
		self.table_summary.setHorizontalHeaderLabels(["Active Case", "Grid Dimensions", "Save State", "Validation Status"])
		self.table_summary.verticalHeader().setVisible(False)
		self.table_summary.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.table_summary.setFixedHeight(72)
		self.table_summary.setShowGrid(True)
		
		# Set blank items
		for col in range(4):
			self.table_summary.setItem(0, col, QTableWidgetItem("—"))

		top_container = QWidget(self)
		top_lay = QVBoxLayout(top_container)
		top_lay.setContentsMargins(20, 16, 20, 0)
		top_lay.addWidget(self.table_summary)

		# ── Log Output Canvas ─────────────────────────────────────────────────
		_log_header = QLabel("  Run Log", self)
		_log_header.setObjectName("dashCardTitle")
		_log_header.setContentsMargins(20, 10, 0, 4)

		self._log = QTextEdit(self)
		self._log.setObjectName("logOutput")
		self._log.setReadOnly(True)
		self._log.setPlaceholderText("Log simulasi akan muncul di sini saat run dimulai…")
		self._log.setMaximumHeight(280)

		# ── Root Layout ──────────────────────────────────────────────────────
		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(self._progress)
		root.addWidget(top_container)
		root.addWidget(_log_header)
		_log_wrap = QWidget(self)
		_log_wrap.setObjectName("dashContent")
		_lw = QVBoxLayout(_log_wrap)
		_lw.setContentsMargins(20, 4, 20, 20)
		_lw.addWidget(self._log)
		root.addWidget(_log_wrap)
		root.addStretch(1)

		self._run_btn.clicked.connect(self.runRequested)
		self._stop_btn.clicked.connect(self.cancelRequested)

	# ── Public API ────────────────────────────────────────────────────────────
	def set_project_state(self, project_config: ProjectConfig, validation_errors: list[str]) -> None:
		gs = project_config.grid_spec
		cells = gs.nx * gs.ny * gs.nz
		
		# Set Case Item
		self.table_summary.setItem(0, 0, QTableWidgetItem(project_config.run.case_name))
		
		# Set Grid Item
		self.table_summary.setItem(0, 1, QTableWidgetItem(f"{gs.nx} × {gs.ny} × {gs.nz}  ({cells:,} sel)"))
		
		# Set State Item
		if project_config.is_dirty:
			item_state = QTableWidgetItem("Belum Disimpan")
			item_state.setForeground(QBrush(QColor("#A86A15")))
		else:
			item_state = QTableWidgetItem("Up-to-date")
			item_state.setForeground(QBrush(QColor("#2D6A4F")))
		self.table_summary.setItem(0, 2, item_state)

		# Set Validation Status Item
		if validation_errors:
			item_status = QTableWidgetItem("Blocked (Ada Hambatan)")
			item_status.setForeground(QBrush(QColor("#B2413F")))
			self._run_btn.setEnabled(False)
		else:
			item_status = QTableWidgetItem("Ready")
			item_status.setForeground(QBrush(QColor("#2D6A4F")))
			self._run_btn.setEnabled(True)
		self.table_summary.setItem(0, 3, item_status)

	def set_running(self, running: bool) -> None:
		self._run_btn.setEnabled(not running)
		self._stop_btn.setEnabled(running)
		self._progress.setVisible(running)

	def clear_log(self) -> None:
		self._log.clear()

	def append_log(self, message: str) -> None:
		self._log.append(message)
		sb = self._log.verticalScrollBar()
		sb.setValue(sb.maximum())

	def set_run_feedback(self, message: str) -> None:
		# Update Validation Status column with feedback
		item_feedback = QTableWidgetItem(message)
		item_feedback.setForeground(QBrush(QColor("#0F5C8E")))
		self.table_summary.setItem(0, 3, item_feedback)
		self.append_log(message)

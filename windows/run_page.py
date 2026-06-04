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
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


class RunPage(QWidget):
	runRequested    = Signal()
	cancelRequested = Signal()

	def __init__(self) -> None:
		super().__init__()

		# ── Header bar ───────────────────────────────────────────────────────
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

		self._stop_btn = QPushButton("■  Stop", self._header)
		self._stop_btn.setObjectName("runBtnStop")
		self._stop_btn.setFixedWidth(110)
		self._stop_btn.setEnabled(False)

		_hrow.addWidget(_title)
		_hrow.addStretch(1)
		_hrow.addWidget(self._run_btn)
		_hrow.addWidget(self._stop_btn)

		# ── Progress bar ─────────────────────────────────────────────────────
		self._progress = QProgressBar(self)
		self._progress.setObjectName("runProgress")
		self._progress.setRange(0, 0)   # indeterminate by default
		self._progress.setFixedHeight(4)
		self._progress.setTextVisible(False)
		self._progress.setVisible(False)

		# ── Info cards row ───────────────────────────────────────────────────
		cards_row = QHBoxLayout()
		cards_row.setSpacing(16)
		cards_row.setContentsMargins(20, 16, 20, 0)

		self._card_case  = self._make_card("Active Case")
		self._lbl_case   = self._add_row(self._card_case, "Case", "—")
		self._lbl_grid   = self._add_row(self._card_case, "Grid", "—")
		self._lbl_state  = self._add_row(self._card_case, "State", "—")

		self._card_valid = self._make_card("Validation")
		self._lbl_status = self._add_row(self._card_valid, "Status", "—")
		self._lbl_issues = self._add_row(self._card_valid, "Issues", "—")

		cards_row.addWidget(self._card_case)
		cards_row.addWidget(self._card_valid)

		# ── Log output ───────────────────────────────────────────────────────
		_log_header = QLabel("  Run Log", self)
		_log_header.setObjectName("dashCardTitle")
		_log_header.setContentsMargins(20, 10, 0, 4)

		self._log = QTextEdit(self)
		self._log.setObjectName("logOutput")
		self._log.setReadOnly(True)
		self._log.setPlaceholderText("Log simulasi akan muncul di sini saat run dimulai…")

		# ── Root layout ──────────────────────────────────────────────────────
		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(self._progress)
		root.addLayout(cards_row)
		root.addWidget(_log_header)
		_log_wrap = QWidget(self)
		_log_wrap.setObjectName("dashContent")
		_lw = QVBoxLayout(_log_wrap)
		_lw.setContentsMargins(20, 4, 20, 20)
		_lw.addWidget(self._log)
		root.addWidget(_log_wrap, 1)

		self._run_btn.clicked.connect(self.runRequested)
		self._stop_btn.clicked.connect(self.cancelRequested)

	# ── Card helpers ─────────────────────────────────────────────────────────
	@staticmethod
	def _make_card(title: str) -> QFrame:
		card = QFrame()
		card.setObjectName("dashCard")
		card.setStyleSheet(
			"QFrame#dashCard { background: #ffffff; border: 1px solid #dde6ee; "
			"border-left: 4px solid #5b9ec9; border-radius: 6px; }"
		)
		lay = QVBoxLayout(card)
		lay.setContentsMargins(14, 10, 14, 12)
		lay.setSpacing(6)
		lbl = QLabel(title.upper())
		lbl.setObjectName("dashCardTitle")
		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("dashCardSep")
		lay.addWidget(lbl)
		lay.addWidget(sep)
		return card

	@staticmethod
	def _add_row(card: QFrame, label: str, value: str) -> QLabel:
		row = QHBoxLayout()
		row.setContentsMargins(0, 0, 0, 0)
		lbl = QLabel(label)
		lbl.setObjectName("dashRowLabel")
		lbl.setFixedWidth(70)
		val = QLabel(value)
		val.setObjectName("dashRowValue")
		val.setWordWrap(True)
		row.addWidget(lbl)
		row.addWidget(val, 1)
		card.layout().addLayout(row)
		return val

	# ── Public API ────────────────────────────────────────────────────────────
	def set_project_state(self, project_config: ProjectConfig, validation_errors: list[str]) -> None:
		gs = project_config.grid_spec
		cells = gs.nx * gs.ny * gs.nz
		self._lbl_case.setText(project_config.run.case_name)
		self._lbl_grid.setText(f"{gs.nx} × {gs.ny} × {gs.nz}  ({cells:,} sel)")
		if project_config.is_dirty:
			self._lbl_state.setText("Dirty — run ulang disarankan")
			self._lbl_state.setStyleSheet("color: #e6a817;")
		else:
			self._lbl_state.setText("Clean")
			self._lbl_state.setStyleSheet("color: #4caf7d;")

		if validation_errors:
			self._lbl_status.setText("Blocked")
			self._lbl_status.setStyleSheet("color: #d9534f; font-weight: bold;")
			self._lbl_issues.setText(" • " + "\n • ".join(validation_errors))
			self._lbl_issues.setStyleSheet("color: #d9534f;")
			self._run_btn.setEnabled(False)
		else:
			self._lbl_status.setText("Ready")
			self._lbl_status.setStyleSheet("color: #4caf7d; font-weight: bold;")
			self._lbl_issues.setText("Semua validasi lolos")
			self._lbl_issues.setStyleSheet("color: #4a6278;")
			self._run_btn.setEnabled(True)

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
		self._lbl_status.setText(message)
		self.append_log(message)


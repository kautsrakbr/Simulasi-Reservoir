from __future__ import annotations

from math import isclose

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
	QFrame,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QProgressBar,
	QPushButton,
	QSizePolicy,
	QSplitter,
	QTextEdit,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig


# ── Live Residual Chart ──────────────────────────────────────────────────────

class LiveResidualChart(QWidget):
	"""Real-time QPainter residual history chart."""

	_LINE_COLOR = QColor("#0F5C8E")
	_DOT_COLOR = QColor("#0F5C8E")
	_BG = QColor("#FFFFFF")
	_GRID_COLOR = QColor("#EEF2F6")
	_AXIS_COLOR = QColor("#D7DEE7")
	_TEXT_COLOR = QColor("#5B6676")

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._times: list[float] = []
		self._residuals: list[float] = []
		self.setMinimumHeight(160)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	def add_point(self, time_days: float, residual: float) -> None:
		if residual > 0.0:
			self._times.append(time_days)
			self._residuals.append(residual)
			self.update()

	def clear(self) -> None:
		self._times.clear()
		self._residuals.clear()
		self.update()

	def paintEvent(self, _event) -> None:  # noqa: N802
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		W, H = self.width(), self.height()
		PL, PT, PR, PB = 58, 14, 14, 32

		painter.fillRect(0, 0, W, H, self._BG)

		px, py = PL, PT
		pw = W - PL - PR
		ph = H - PT - PB

		if pw <= 0 or ph <= 0:
			return

		# Grid
		painter.setPen(QPen(self._GRID_COLOR, 1))
		for i in range(5):
			y = int(py + i * ph / 4)
			painter.drawLine(px, y, px + pw, y)

		# Border
		painter.setPen(QPen(self._AXIS_COLOR, 1))
		painter.drawRect(px, py, pw, ph)

		# No data
		if len(self._residuals) < 2:
			painter.setPen(self._TEXT_COLOR)
			painter.setFont(QFont("Segoe UI", 9))
			painter.drawText(
				px + 8, py, pw - 8, ph,
				Qt.AlignmentFlag.AlignCenter,
				"Residual history akan muncul saat run berjalan...",
			)
			return

		max_r = max(self._residuals)
		min_r = min(self._residuals)
		if isclose(max_r, min_r):
			max_r = min_r + 1.0
		max_t = max(self._times)
		min_t = min(self._times)
		if isclose(max_t, min_t):
			max_t = min_t + 1.0

		# Y labels
		painter.setFont(QFont("Segoe UI", 7))
		painter.setPen(self._TEXT_COLOR)
		for i in range(5):
			frac = 1.0 - i / 4.0
			val = min_r + frac * (max_r - min_r)
			y = int(py + i * ph / 4)
			painter.drawText(0, y - 6, PL - 4, 14, Qt.AlignmentFlag.AlignRight, f"{val:.2e}")

		# X labels
		for i in range(5):
			frac = i / 4.0
			val = min_t + frac * (max_t - min_t)
			x = int(px + frac * pw)
			painter.drawText(x - 20, py + ph + 4, 40, 16, Qt.AlignmentFlag.AlignCenter, f"{val:.1f}")

		# X axis title
		painter.drawText(px, py + ph + 20, pw, 12, Qt.AlignmentFlag.AlignCenter, "Simulation Time (days)")

		# Plot line
		pen = QPen(self._LINE_COLOR, 2.0)
		pen.setCapStyle(Qt.PenCapStyle.RoundCap)
		pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
		painter.setPen(pen)

		def _s(t: float, r: float) -> tuple[int, int]:
			sx = px + int((t - min_t) / (max_t - min_t) * pw)
			sy = py + int(ph - (r - min_r) / (max_r - min_r) * ph)
			return sx, sy

		for i in range(len(self._residuals) - 1):
			x1, y1 = _s(self._times[i], self._residuals[i])
			x2, y2 = _s(self._times[i + 1], self._residuals[i + 1])
			painter.drawLine(x1, y1, x2, y2)

		# Last point
		lx, ly = _s(self._times[-1], self._residuals[-1])
		painter.setBrush(self._DOT_COLOR)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.drawEllipse(lx - 4, ly - 4, 8, 8)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _metric_pair(label: str) -> tuple[QHBoxLayout, QLabel]:
	row = QHBoxLayout()
	row.setContentsMargins(0, 0, 0, 0)
	row.setSpacing(4)
	lbl = QLabel(label)
	lbl.setObjectName("metaLabel")
	lbl.setFixedWidth(116)
	val = QLabel("\u2014")
	val.setObjectName("metaValue")
	row.addWidget(lbl)
	row.addWidget(val, 1)
	return row, val


# ── Run Page ─────────────────────────────────────────────────────────────────

class RunPage(QWidget):
	runRequested = Signal()
	cancelRequested = Signal()

	def __init__(self) -> None:
		super().__init__()
		self._is_running = False

		outer = QVBoxLayout(self)
		outer.setContentsMargins(24, 20, 24, 20)
		outer.setSpacing(12)

		# ── Page header ──
		hdr = QHBoxLayout()
		title_lbl = QLabel("Run Simulation")
		title_lbl.setObjectName("pageTitle")
		self.status_badge = QLabel("Idle")
		self.status_badge.setObjectName("metaLabel")
		self.status_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		hdr.addWidget(title_lbl)
		hdr.addWidget(self.status_badge, 1)
		outer.addLayout(hdr)

		# ── Main splitter: left panel | right panel ──
		main_splitter = QSplitter(Qt.Orientation.Horizontal)
		main_splitter.setHandleWidth(1)

		# ── LEFT: controls + metrics ──
		left_widget = QWidget()
		left_widget.setMinimumWidth(230)
		left_widget.setMaximumWidth(290)
		left_layout = QVBoxLayout(left_widget)
		left_layout.setContentsMargins(0, 0, 8, 0)
		left_layout.setSpacing(10)

		# Run control group
		ctrl_grp = QGroupBox("Run Control")
		ctrl_box = QVBoxLayout(ctrl_grp)
		ctrl_box.setSpacing(8)

		self.run_button = QPushButton("\u25b6   Run Simulation")
		self.run_button.setObjectName("btnRunBig")
		self.cancel_button = QPushButton("\u25a0   Stop")
		self.cancel_button.setObjectName("btnStopBig")
		self.cancel_button.setEnabled(False)

		self.progress_bar = QProgressBar()
		self.progress_bar.setObjectName("progressLarge")
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		self.progress_bar.setTextVisible(False)

		self.eta_label = QLabel("ETA  \u2014")
		self.eta_label.setObjectName("metaLabel")

		ctrl_box.addWidget(self.run_button)
		ctrl_box.addWidget(self.cancel_button)
		ctrl_box.addWidget(self.progress_bar)
		ctrl_box.addWidget(self.eta_label)
		left_layout.addWidget(ctrl_grp)

		# Step metrics group
		step_grp = QGroupBox("Current Step")
		step_box = QVBoxLayout(step_grp)
		step_box.setSpacing(5)
		r1, self._m_step = _metric_pair("Step")
		r2, self._m_time = _metric_pair("Sim. time")
		r3, self._m_dt = _metric_pair("dt")
		r4, self._m_newton = _metric_pair("Newton iter")
		r5, self._m_residual = _metric_pair("Max residual")
		r6, self._m_target = _metric_pair("Target time")
		for r in (r1, r2, r3, r4, r5, r6):
			step_box.addLayout(r)
		left_layout.addWidget(step_grp)

		# Model info group
		info_grp = QGroupBox("Model Info")
		info_box = QVBoxLayout(info_grp)
		info_box.setSpacing(4)
		self.project_label = QLabel()
		self.project_label.setObjectName("metaLabel")
		self.project_label.setWordWrap(True)
		self.grid_label = QLabel()
		self.grid_label.setObjectName("metaLabel")
		self.dirty_label = QLabel()
		self.dirty_label.setObjectName("metaLabel")
		self.dirty_label.setWordWrap(True)
		self.validation_label = QLabel()
		self.validation_label.setObjectName("metaLabel")
		self.validation_label.setWordWrap(True)
		self.status_label = QLabel()
		self.status_label.setObjectName("metaLabel")
		for lbl in (self.project_label, self.grid_label, self.dirty_label,
					self.validation_label, self.status_label):
			info_box.addWidget(lbl)
		left_layout.addWidget(info_grp)
		left_layout.addStretch(1)

		main_splitter.addWidget(left_widget)

		# ── RIGHT: chart + log ──
		right_splitter = QSplitter(Qt.Orientation.Vertical)
		right_splitter.setHandleWidth(4)

		chart_frame = QFrame()
		chart_frame.setObjectName("card")
		chart_box = QVBoxLayout(chart_frame)
		chart_box.setContentsMargins(12, 10, 12, 10)
		chart_box.setSpacing(6)
		chart_hdr = QHBoxLayout()
		chart_hdr.addWidget(QLabel("Live Residual Chart"))
		chart_hdr.addStretch()
		self._chart_info = QLabel("\u25cf  Residual vs. Time")
		self._chart_info.setObjectName("metaLabel")
		chart_hdr.addWidget(self._chart_info)
		chart_box.addLayout(chart_hdr)
		self.live_chart = LiveResidualChart()
		chart_box.addWidget(self.live_chart, 1)
		right_splitter.addWidget(chart_frame)

		log_frame = QFrame()
		log_frame.setObjectName("card")
		log_box = QVBoxLayout(log_frame)
		log_box.setContentsMargins(0, 0, 0, 0)
		log_box.setSpacing(0)
		log_hdr = QWidget()
		log_hdr.setFixedHeight(32)
		log_hdr_box = QHBoxLayout(log_hdr)
		log_hdr_box.setContentsMargins(12, 0, 12, 0)
		log_hdr_box.addWidget(QLabel("Runtime Log"))
		log_box.addWidget(log_hdr)
		self.runtime_log = QTextEdit()
		self.runtime_log.setObjectName("logOutput")
		self.runtime_log.setReadOnly(True)
		self.runtime_log.setPlaceholderText("Runtime progress akan muncul di sini...")
		log_box.addWidget(self.runtime_log, 1)
		right_splitter.addWidget(log_frame)

		right_splitter.setSizes([300, 160])
		main_splitter.addWidget(right_splitter)
		main_splitter.setSizes([265, 900])
		outer.addWidget(main_splitter, 1)

		self.run_button.clicked.connect(self.runRequested)
		self.cancel_button.clicked.connect(self.cancelRequested)

	# ── Public API (compatible with main_window.py) ───────────────────────────

	def set_project_state(self, project_config: ProjectConfig, validation_errors: list[str]) -> None:
		self.project_label.setText(f"Case:  {project_config.run.case_name}")
		cell_count = (
			project_config.grid_spec.nx
			* project_config.grid_spec.ny
			* project_config.grid_spec.nz
		)
		self.grid_label.setText(
			f"Grid:  {project_config.grid_spec.nx}"
			f"\u00d7{project_config.grid_spec.ny}"
			f"\u00d7{project_config.grid_spec.nz}"
			f"  ({cell_count} cells)"
		)
		self._m_target.setText(f"{project_config.solver.max_time_days:.2f} days")
		self.dirty_label.setText(
			"\u26a0 Model changed \u2014 run ulang disarankan" if project_config.is_dirty
			else "\u2713 Model synchronized"
		)
		if validation_errors:
			if not self._is_running:
				self.status_label.setText("Status:  Blocked")
				self._set_badge("Blocked", "statusError")
			self.validation_label.setText("Issues:  " + " | ".join(validation_errors))
			self.run_button.setEnabled(False)
		else:
			if not self._is_running:
				self.status_label.setText("Status:  Ready")
				self._set_badge("Ready", "statusReady")
			self.validation_label.setText("\u2713 All checks passed")
			self.run_button.setEnabled(not self._is_running)

	def set_run_feedback(self, message: str) -> None:
		self.status_label.setText(message)
		msg_lower = message.lower()
		if "running" in msg_lower:
			self._set_badge("Running", "statusRunning")
		elif "done" in msg_lower:
			self._set_badge("Done", "statusDone")
		elif "fail" in msg_lower:
			self._set_badge("Failed", "statusError")
		elif "cancel" in msg_lower:
			self._set_badge("Canceled", "statusWarning")

	def set_running(self, is_running: bool) -> None:
		self._is_running = is_running
		self.run_button.setEnabled(not is_running)
		self.cancel_button.setEnabled(is_running)
		if is_running:
			self.set_progress(0.0, "calculating...")
			self.live_chart.clear()
			for lbl in (self._m_step, self._m_time, self._m_dt, self._m_newton, self._m_residual):
				lbl.setText("\u2014")

	def clear_runtime_log(self) -> None:
		self.runtime_log.clear()

	def append_runtime_log(self, message: str) -> None:
		if message.strip():
			self.runtime_log.append(message)

	def set_progress(self, percent: float, eta_text: str) -> None:
		clamped = max(0.0, min(100.0, percent))
		self.progress_bar.setValue(int(round(clamped)))
		self.eta_label.setText(f"ETA  {eta_text}" if eta_text else "ETA  \u2014")

	def add_residual_point(self, time_days: float, residual: float) -> None:
		self.live_chart.add_point(time_days, residual)

	def update_step_metrics(
		self,
		step: int,
		time_days: float,
		dt_days: float,
		newton_iters: int,
		residual: float,
	) -> None:
		self._m_step.setText(str(step))
		self._m_time.setText(f"{time_days:.3f} days")
		self._m_dt.setText(f"{dt_days:.4f} days")
		self._m_newton.setText(str(newton_iters))
		self._m_residual.setText(f"{residual:.4e}")

	def _set_badge(self, text: str, obj_name: str) -> None:
		self.status_badge.setText(text)
		self.status_badge.setObjectName(obj_name)
		self.status_badge.style().polish(self.status_badge)

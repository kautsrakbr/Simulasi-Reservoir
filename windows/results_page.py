from __future__ import annotations

from math import isclose

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
	QAbstractItemView,
	QPushButton,
	QComboBox,
	QFrame,
	QHeaderView,
	QHBoxLayout,
	QLabel,
	QTabWidget,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.results import RunResult

from modules.results_service import get_run_summary


class TrendChartWidget(QWidget):
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._title = "Residual Trend"
		self._series: dict[str, list[float]] = {}
		self._colors = [
			QColor("#2f6f66"),
			QColor("#d95f02"),
			QColor("#3f88c5"),
			QColor("#845ec2"),
		]
		self.setMinimumHeight(220)

	def set_data(self, title: str, series: dict[str, list[float]]) -> None:
		self._title = title
		self._series = series
		self.update()

	def paintEvent(self, _event) -> None:  # noqa: N802
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		rect = self.rect().adjusted(8, 8, -8, -8)
		painter.setPen(QPen(QColor("#c9d8d2"), 1.0))
		painter.setBrush(QColor("#fdfefd"))
		painter.drawRoundedRect(rect, 10, 10)

		painter.setPen(QColor("#25423d"))
		painter.drawText(rect.adjusted(12, 10, -12, -10), self._title)

		if not self._series:
			painter.setPen(QColor("#6f7f7a"))
			painter.drawText(rect.adjusted(12, 32, -12, -12), "Belum ada data trend untuk ditampilkan.")
			return

		plot = rect.adjusted(48, 42, -24, -30)
		all_values = [value for values in self._series.values() for value in values]
		if not all_values:
			return

		min_y = min(all_values)
		max_y = max(all_values)
		if isclose(min_y, max_y):
			max_y = min_y + 1.0

		painter.setPen(QPen(QColor("#d9e4df"), 1.0))
		for row in range(5):
			y = plot.top() + row * plot.height() / 4.0
			painter.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))

		painter.setPen(QPen(QColor("#9fb2aa"), 1.0))
		painter.drawRect(plot)

		for series_index, (name, values) in enumerate(self._series.items()):
			if len(values) < 2:
				continue
			color = self._colors[series_index % len(self._colors)]
			pen = QPen(color, 2.0)
			painter.setPen(pen)

			for index in range(len(values) - 1):
				x1 = plot.left() + (index / (len(values) - 1)) * plot.width()
				x2 = plot.left() + ((index + 1) / (len(values) - 1)) * plot.width()
				y1 = plot.bottom() - ((values[index] - min_y) / (max_y - min_y)) * plot.height()
				y2 = plot.bottom() - ((values[index + 1] - min_y) / (max_y - min_y)) * plot.height()
				painter.drawLine(int(x1), int(y1), int(x2), int(y2))

		legend_x = plot.left()
		legend_y = rect.bottom() - 10
		for series_index, name in enumerate(self._series):
			color = self._colors[series_index % len(self._colors)]
			painter.setPen(QPen(color, 3.0))
			painter.drawLine(legend_x, legend_y, legend_x + 16, legend_y)
			painter.setPen(QColor("#2a3d39"))
			painter.drawText(legend_x + 22, legend_y + 4, name)
			legend_x += 120


class ResultsPage(QWidget):
	exportRequested = Signal()

	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Results Page")
		title.setObjectName("pageTitle")
		self.description = QLabel(
			"Halaman ini akan menampilkan summary, trend, map, dan table hasil simulasi."
		)
		self.description.setWordWrap(True)

		summary_card = QFrame(self)
		summary_card.setObjectName("card")
		summary_layout = QVBoxLayout(summary_card)
		self.summary_label = QLabel("Belum ada hasil run.")
		self.summary_label.setWordWrap(True)
		self.warning_label = QLabel()
		self.warning_label.setWordWrap(True)
		summary_layout.addWidget(self.summary_label)
		summary_layout.addWidget(self.warning_label)

		chart_card = QFrame(self)
		chart_card.setObjectName("card")
		chart_layout = QVBoxLayout(chart_card)
		chart_title = QLabel("Residual Chart")
		chart_title.setObjectName("sectionTitle")
		self.trend_chart = TrendChartWidget(self)
		chart_layout.addWidget(chart_title)
		chart_layout.addWidget(self.trend_chart)
		self.export_button = QPushButton("Export Summary", self)
		self.export_button.setEnabled(False)
		self.retry_scope_combo = QComboBox(self)
		self.retry_scope_combo.addItems(["Latest Step Only", "All Steps"])
		self.retry_status_combo = QComboBox(self)
		self.retry_status_combo.addItems(["All Attempts", "Rejected Only", "Accepted Only"])
		self.retry_stats_label = QLabel("Retry table: 0 row(s)")
		self.trend_stats_label = QLabel("Trend table: 0 row(s)")
		self.trend_table = QTableWidget(0, 10, self)
		self.trend_table.setHorizontalHeaderLabels(
			[
				"Step",
				"Time (days)",
				"Duration (s)",
				"Retries",
				"Newton Iter",
				"Max Residual",
				"Oil Residual",
				"Water Residual",
				"Gas Residual",
				"Converged",
			]
		)
		self.trend_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.trend_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
		self.trend_table.setSortingEnabled(True)
		self.trend_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.trend_table.verticalHeader().setVisible(False)
		self.retry_table = QTableWidget(0, 7, self)
		self.retry_table.setHorizontalHeaderLabels(
			[
				"Step",
				"Retry",
				"Target Time (days)",
				"dt (days)",
				"Max Residual",
				"Residual Norm",
				"Status",
			]
		)
		self.retry_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.retry_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
		self.retry_table.setSortingEnabled(True)
		self.retry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.retry_table.verticalHeader().setVisible(False)
		self.detail_label = QLabel()
		self.detail_label.setWordWrap(True)
		self._active_run_result: RunResult | None = None

		retry_toolbar = QHBoxLayout()
		retry_toolbar.addWidget(QLabel("Retry Scope", self))
		retry_toolbar.addWidget(self.retry_scope_combo)
		retry_toolbar.addWidget(QLabel("Status Filter", self))
		retry_toolbar.addWidget(self.retry_status_combo)
		retry_toolbar.addWidget(self.retry_stats_label, 1)

		trend_toolbar = QHBoxLayout()
		trend_toolbar.addWidget(QLabel("Phase Residual Trend", self))
		trend_toolbar.addWidget(self.trend_stats_label, 1)
		trend_toolbar.addWidget(self.export_button)

		# ── Page header ───────────────────────────────────────────────
		hdr_row = QHBoxLayout()
		hdr_row.addWidget(title)
		hdr_row.addStretch()
		hdr_row.addWidget(self.export_button)
		layout.addLayout(hdr_row)
		layout.addWidget(self.description)

		# ── Tab widget ─────────────────────────────────────────────────
		tabs = QTabWidget()

		# Tab 0: Summary
		summary_tab = QWidget()
		summary_tab_box = QVBoxLayout(summary_tab)
		summary_tab_box.setContentsMargins(16, 16, 16, 16)
		summary_tab_box.addWidget(summary_card)
		summary_tab_box.addStretch()
		tabs.addTab(summary_tab, "Summary")

		# Tab 1: Trends
		trend_tab = QWidget()
		trend_tab_box = QVBoxLayout(trend_tab)
		trend_tab_box.setContentsMargins(8, 8, 8, 8)
		trend_tab_box.addWidget(chart_card)
		trend_tab_box.addLayout(trend_toolbar)
		trend_tab_box.addWidget(self.trend_table, 1)
		tabs.addTab(trend_tab, "Trends")

		# Tab 2: Retry Log
		retry_tab = QWidget()
		retry_tab_box = QVBoxLayout(retry_tab)
		retry_tab_box.setContentsMargins(8, 8, 8, 8)
		retry_tab_box.addLayout(retry_toolbar)
		retry_tab_box.addWidget(self.retry_table, 1)
		tabs.addTab(retry_tab, "Retry Log")

		# Tab 3: Cell Detail
		detail_tab = QWidget()
		detail_tab_box = QVBoxLayout(detail_tab)
		detail_tab_box.setContentsMargins(16, 16, 16, 16)
		detail_tab_box.addWidget(self.detail_label)
		detail_tab_box.addStretch()
		tabs.addTab(detail_tab, "Cell Detail")

		layout.addWidget(tabs, 1)

		self.retry_scope_combo.currentIndexChanged.connect(self._refresh_retry_table)
		self.retry_status_combo.currentIndexChanged.connect(self._refresh_retry_table)
		self.export_button.clicked.connect(self.exportRequested)

	def set_run_result(self, run_result: RunResult | None) -> None:
		self._active_run_result = run_result
		if run_result is None:
			self.summary_label.setText("Belum ada hasil run.")
			self.warning_label.setText("")
			self.trend_chart.set_data("Residual Trend", {})
			self.export_button.setEnabled(False)
			self.trend_table.setRowCount(0)
			self.trend_stats_label.setText("Trend table: 0 row(s)")
			self.retry_table.setRowCount(0)
			self.retry_stats_label.setText("Retry table: 0 row(s)")
			self.detail_label.setText("")
			return

		summary = get_run_summary(run_result)
		self.export_button.setEnabled(True)
		latest_step = run_result.steps[-1] if run_result.steps else None
		self.summary_label.setText(
			"Summary: "
			f"steps={summary['step_count']}, "
			f"final_time={summary['final_time_days']}, "
			f"max_residual={summary['last_max_residual']}, "
			f"oil_res={summary['last_max_oil_residual']}, "
			f"water_res={summary['last_max_water_residual']}, "
			f"gas_res={summary['last_max_gas_residual']}, "
			f"mean_trans={summary['last_mean_transmissibility']}, "
			f"max_flux={summary['last_max_connection_flux']}, "
			f"max_accum={summary['last_max_abs_accumulation']}, "
			f"attempts={summary['retry_attempt_count']}, "
			f"rejected={summary['rejected_attempt_count']}, "
			f"converged={summary['last_converged']}"
		)
		if run_result.warnings:
			self.warning_label.setText("Warnings: " + " | ".join(run_result.warnings))
		else:
			self.warning_label.setText("Warnings: none")

		self.trend_chart.set_data(
			"Residual Trend per Step",
			{
				"Max": [step.summary.max_residual for step in run_result.steps],
				"Oil": [step.max_oil_residual for step in run_result.steps],
				"Water": [step.max_water_residual for step in run_result.steps],
				"Gas": [step.max_gas_residual for step in run_result.steps],
			},
		)
		self._refresh_trend_table()
		self._refresh_retry_table()

		if latest_step and latest_step.pressure:
			cell0_accumulation = latest_step.accumulation_per_cell[0] if latest_step.accumulation_per_cell else 0.0
			cell0_residual = latest_step.residual_per_cell[0] if latest_step.residual_per_cell else 0.0
			cell0_oil_residual = latest_step.oil_residual_per_cell[0] if latest_step.oil_residual_per_cell else 0.0
			cell0_water_residual = latest_step.water_residual_per_cell[0] if latest_step.water_residual_per_cell else 0.0
			cell0_gas_residual = latest_step.gas_residual_per_cell[0] if latest_step.gas_residual_per_cell else 0.0
			self.detail_label.setText(
				"Cell 0: "
				f"P={latest_step.pressure[0]:.2f}, "
				f"Sw={latest_step.sw[0]:.4f}, "
				f"Sg={latest_step.sg[0]:.4f}, "
				f"So={latest_step.so[0]:.4f}, "
				f"Accum={cell0_accumulation:.4f}, "
				f"Residual={cell0_residual:.4f}, "
				f"OilRes={cell0_oil_residual:.4f}, "
				f"WaterRes={cell0_water_residual:.4f}, "
				f"GasRes={cell0_gas_residual:.4f}"
			)
		else:
			self.detail_label.setText("Detail hasil belum tersedia.")

	def _build_retry_rows(self, run_result: RunResult) -> list[tuple[int, int, float, float, float, float, str]]:
		rows: list[tuple[int, int, float, float, float, float, str]] = []

		step_indices = range(1, len(run_result.steps) + 1)
		if self.retry_scope_combo.currentText() == "Latest Step Only" and run_result.steps:
			step_indices = [len(run_result.steps)]

		for step_index in step_indices:
			step = run_result.steps[step_index - 1]
			for attempt in step.attempts:
				if self.retry_status_combo.currentText() == "Rejected Only" and attempt.converged:
					continue
				if self.retry_status_combo.currentText() == "Accepted Only" and not attempt.converged:
					continue
				rows.append(
					(
						step_index,
						attempt.retry_index,
						attempt.target_time_days,
						attempt.dt_days,
						attempt.max_residual,
						attempt.residual_norm,
						attempt.note,
					)
				)
		return rows

	def _refresh_trend_table(self) -> None:
		run_result = self._active_run_result
		if run_result is None:
			self.trend_table.setRowCount(0)
			self.trend_stats_label.setText("Trend table: 0 row(s)")
			return

		self.trend_table.setSortingEnabled(False)
		self.trend_table.setRowCount(len(run_result.steps))
		for row_index, step in enumerate(run_result.steps):
			row_values: list[float | int | str] = [
				row_index + 1,
				step.summary.time_days,
				step.summary.step_duration_seconds,
				step.summary.retry_count,
				step.summary.newton_iterations,
				step.summary.max_residual,
				step.max_oil_residual,
				step.max_water_residual,
				step.max_gas_residual,
				"yes" if step.summary.converged else "no",
			]
			for col_index, value in enumerate(row_values):
				if isinstance(value, float):
					cell_text = f"{value:.6f}"
				else:
					cell_text = str(value)
				item = QTableWidgetItem(cell_text)
				if col_index == 9:
					if value == "yes":
						item.setBackground(QColor("#dff6dd"))
					else:
						item.setBackground(QColor("#f8d7da"))
				self.trend_table.setItem(row_index, col_index, item)

		self.trend_table.setSortingEnabled(True)
		self.trend_table.sortByColumn(0, self.trend_table.horizontalHeader().sortIndicatorOrder())
		self.trend_stats_label.setText(f"Trend table: {len(run_result.steps)} row(s)")

	def _refresh_retry_table(self) -> None:
		run_result = self._active_run_result
		if run_result is None:
			self.retry_table.setRowCount(0)
			self.retry_stats_label.setText("Retry table: 0 row(s)")
			return

		rows = self._build_retry_rows(run_result)
		self.retry_table.setSortingEnabled(False)
		self.retry_table.setRowCount(len(rows))
		for row_index, row_data in enumerate(rows):
			for col_index, value in enumerate(row_data):
				if isinstance(value, float):
					cell_text = f"{value:.6f}"
				else:
					cell_text = str(value)
				item = QTableWidgetItem(cell_text)
				if col_index == 6:
					status_value = str(value)
					if status_value == "accepted":
						item.setBackground(QColor("#dff6dd"))
					elif status_value == "abort-min-dt":
						item.setBackground(QColor("#f8d7da"))
					else:
						item.setBackground(QColor("#fff3cd"))
				self.retry_table.setItem(row_index, col_index, item)

		self.retry_table.setSortingEnabled(True)
		self.retry_table.sortByColumn(0, self.retry_table.horizontalHeader().sortIndicatorOrder())
		self.retry_stats_label.setText(f"Retry table: {len(rows)} row(s)")

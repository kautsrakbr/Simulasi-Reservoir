from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QHeaderView,
	QHBoxLayout,
	QLabel,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from engine.domain.results import RunResult

from modules.results_service import get_run_summary


class ResultsPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		layout = QVBoxLayout(self)
		title = QLabel("Results Page")
		self.description = QLabel(
			"Halaman ini akan menampilkan summary, trend, map, dan table hasil simulasi."
		)
		self.description.setWordWrap(True)
		self.summary_label = QLabel("Belum ada hasil run.")
		self.summary_label.setWordWrap(True)
		self.warning_label = QLabel()
		self.warning_label.setWordWrap(True)
		self.retry_scope_combo = QComboBox(self)
		self.retry_scope_combo.addItems(["Latest Step Only", "All Steps"])
		self.retry_status_combo = QComboBox(self)
		self.retry_status_combo.addItems(["All Attempts", "Rejected Only", "Accepted Only"])
		self.retry_stats_label = QLabel("Retry table: 0 row(s)")
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

		layout.addWidget(title)
		layout.addWidget(self.description)
		layout.addWidget(self.summary_label)
		layout.addWidget(self.warning_label)
		layout.addLayout(retry_toolbar)
		layout.addWidget(self.retry_table)
		layout.addWidget(self.detail_label)

		self.retry_scope_combo.currentIndexChanged.connect(self._refresh_retry_table)
		self.retry_status_combo.currentIndexChanged.connect(self._refresh_retry_table)

	def set_run_result(self, run_result: RunResult | None) -> None:
		self._active_run_result = run_result
		if run_result is None:
			self.summary_label.setText("Belum ada hasil run.")
			self.warning_label.setText("")
			self.retry_table.setRowCount(0)
			self.retry_stats_label.setText("Retry table: 0 row(s)")
			self.detail_label.setText("")
			return

		summary = get_run_summary(run_result)
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

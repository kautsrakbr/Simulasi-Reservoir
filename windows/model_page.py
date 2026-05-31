from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
	QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
	QLabel, QLineEdit, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from engine.domain.project import ProjectConfig


class ModelPage(QWidget):
	projectChanged = Signal(str, str, str, float)
	solverChanged = Signal(float, float, float, float, float, int, int, float, float, float, float, float, float, float)
	SOLVER_PRESETS: dict[str, dict[str, float | int]] = {
		"Stable": {
			"timestep_growth_factor": 1.05,
			"timestep_shrink_factor": 0.4,
			"max_step_retries": 12,
			"max_newton_iterations": 20,
			"residual_tolerance": 0.00005,
			"residual_norm_floor": 0.05,
			"newton_pressure_damping": 0.55,
			"newton_saturation_damping": 0.55,
			"max_pressure_correction": 6.0,
			"max_saturation_correction": 0.001,
		},
		"Balanced": {
			"timestep_growth_factor": 1.1,
			"timestep_shrink_factor": 0.5,
			"max_step_retries": 8,
			"max_newton_iterations": 10,
			"residual_tolerance": 0.0001,
			"residual_norm_floor": 0.1,
			"newton_pressure_damping": 0.7,
			"newton_saturation_damping": 0.7,
			"max_pressure_correction": 10.0,
			"max_saturation_correction": 0.001,
		},
		"Fast": {
			"timestep_growth_factor": 1.25,
			"timestep_shrink_factor": 0.6,
			"max_step_retries": 5,
			"max_newton_iterations": 8,
			"residual_tolerance": 0.0002,
			"residual_norm_floor": 0.2,
			"newton_pressure_damping": 0.85,
			"newton_saturation_damping": 0.85,
			"max_pressure_correction": 15.0,
			"max_saturation_correction": 0.003,
		},
	}

	def __init__(self) -> None:
		super().__init__()

		self.name_input = QLineEdit(self)
		self.description_input = QLineEdit(self)
		self.case_name_input = QLineEdit(self)
		self.solver_preset_input = QLineEdit(self)
		self.solver_preset_input.setReadOnly(True)
		self.solver_preset_input.setText("Custom")
		self.reference_pressure_input = QDoubleSpinBox(self)
		self.reference_pressure_input.setDecimals(2)
		self.reference_pressure_input.setMaximum(1_000_000.0)
		self.initial_timestep_input = QDoubleSpinBox(self)
		self.initial_timestep_input.setDecimals(4)
		self.initial_timestep_input.setRange(0.0001, 3650.0)
		self.min_timestep_input = QDoubleSpinBox(self)
		self.min_timestep_input.setDecimals(6)
		self.min_timestep_input.setRange(0.000001, 3650.0)
		self.max_time_input = QDoubleSpinBox(self)
		self.max_time_input.setDecimals(4)
		self.max_time_input.setRange(0.0001, 36500.0)
		self.timestep_growth_factor_input = QDoubleSpinBox(self)
		self.timestep_growth_factor_input.setDecimals(4)
		self.timestep_growth_factor_input.setRange(1.0, 5.0)
		self.timestep_growth_factor_input.setSingleStep(0.05)
		self.timestep_shrink_factor_input = QDoubleSpinBox(self)
		self.timestep_shrink_factor_input.setDecimals(4)
		self.timestep_shrink_factor_input.setRange(0.05, 0.95)
		self.timestep_shrink_factor_input.setSingleStep(0.05)
		self.max_newton_iterations_input = QSpinBox(self)
		self.max_newton_iterations_input.setRange(1, 200)
		self.max_step_retries_input = QSpinBox(self)
		self.max_step_retries_input.setRange(0, 100)
		self.residual_tolerance_input = QDoubleSpinBox(self)
		self.residual_tolerance_input.setDecimals(10)
		self.residual_tolerance_input.setRange(0.0000000001, 1.0)
		self.residual_tolerance_input.setSingleStep(0.000001)
		self.residual_norm_floor_input = QDoubleSpinBox(self)
		self.residual_norm_floor_input.setDecimals(6)
		self.residual_norm_floor_input.setRange(0.000001, 1.0)
		self.residual_norm_floor_input.setSingleStep(0.01)
		self.parameter_tolerance_input = QDoubleSpinBox(self)
		self.parameter_tolerance_input.setDecimals(10)
		self.parameter_tolerance_input.setRange(0.0000000001, 1.0)
		self.parameter_tolerance_input.setSingleStep(0.000001)
		self.newton_pressure_damping_input = QDoubleSpinBox(self)
		self.newton_pressure_damping_input.setDecimals(4)
		self.newton_pressure_damping_input.setRange(0.05, 1.0)
		self.newton_pressure_damping_input.setSingleStep(0.05)
		self.newton_saturation_damping_input = QDoubleSpinBox(self)
		self.newton_saturation_damping_input.setDecimals(4)
		self.newton_saturation_damping_input.setRange(0.05, 1.0)
		self.newton_saturation_damping_input.setSingleStep(0.05)
		self.max_pressure_correction_input = QDoubleSpinBox(self)
		self.max_pressure_correction_input.setDecimals(4)
		self.max_pressure_correction_input.setRange(0.01, 1_000_000.0)
		self.max_pressure_correction_input.setSingleStep(1.0)
		self.max_saturation_correction_input = QDoubleSpinBox(self)
		self.max_saturation_correction_input.setDecimals(6)
		self.max_saturation_correction_input.setRange(0.000001, 1.0)
		self.max_saturation_correction_input.setSingleStep(0.005)
		self.solver_preset_picker = QComboBox(self)
		self.solver_preset_picker.addItems(["Stable", "Balanced", "Fast"])

		# ── Build QScrollArea + QGroupBox layout ─────────────────────
		outer = QVBoxLayout(self)
		outer.setContentsMargins(24, 20, 24, 20)
		outer.setSpacing(12)

		_title = QLabel("Model & Solver")
		_title.setObjectName("pageTitle")
		outer.addWidget(_title)

		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QScrollArea.Shape.NoFrame)
		_container = QWidget()
		_c = QVBoxLayout(_container)
		_c.setContentsMargins(0, 0, 0, 0)
		_c.setSpacing(14)

		# Project Info
		_grp1 = QGroupBox("Project Info")
		_f1 = QFormLayout(_grp1)
		_f1.setSpacing(8)
		_f1.addRow("Project Name", self.name_input)
		_f1.addRow("Description", self.description_input)
		_f1.addRow("Case Name", self.case_name_input)
		_c.addWidget(_grp1)

		# Reference Data
		_grp2 = QGroupBox("Reference Data")
		_f2 = QFormLayout(_grp2)
		_f2.setSpacing(8)
		_f2.addRow("Reference Pressure (psi)", self.reference_pressure_input)
		_c.addWidget(_grp2)

		# Solver Preset
		_grp3 = QGroupBox("Solver Preset")
		_f3 = QFormLayout(_grp3)
		_f3.setSpacing(8)
		_f3.addRow("Active Preset", self.solver_preset_input)
		_f3.addRow("Apply Preset", self.solver_preset_picker)
		_c.addWidget(_grp3)

		# Time Step Control
		_grp4 = QGroupBox("Time Step Control")
		_f4 = QFormLayout(_grp4)
		_f4.setSpacing(8)
		_f4.addRow("Initial Timestep (days)", self.initial_timestep_input)
		_f4.addRow("Min Timestep (days)", self.min_timestep_input)
		_f4.addRow("Max Time (days)", self.max_time_input)
		_f4.addRow("Timestep Growth Factor", self.timestep_growth_factor_input)
		_f4.addRow("Timestep Shrink Factor", self.timestep_shrink_factor_input)
		_f4.addRow("Max Step Retries", self.max_step_retries_input)
		_c.addWidget(_grp4)

		# Newton Solver
		_grp5 = QGroupBox("Newton Solver")
		_f5 = QFormLayout(_grp5)
		_f5.setSpacing(8)
		_f5.addRow("Max Newton Iterations", self.max_newton_iterations_input)
		_f5.addRow("Residual Tolerance", self.residual_tolerance_input)
		_f5.addRow("Residual Norm Floor", self.residual_norm_floor_input)
		_f5.addRow("Parameter Tolerance", self.parameter_tolerance_input)
		_f5.addRow("Pressure Damping", self.newton_pressure_damping_input)
		_f5.addRow("Saturation Damping", self.newton_saturation_damping_input)
		_f5.addRow("Max Pressure Correction", self.max_pressure_correction_input)
		_f5.addRow("Max Saturation Correction", self.max_saturation_correction_input)
		_c.addWidget(_grp5)
		_c.addStretch(1)

		scroll.setWidget(_container)
		outer.addWidget(scroll, 1)

		self.name_input.editingFinished.connect(self._emit_change)
		self.description_input.editingFinished.connect(self._emit_change)
		self.case_name_input.editingFinished.connect(self._emit_change)
		self.reference_pressure_input.valueChanged.connect(self._emit_change)
		self.initial_timestep_input.valueChanged.connect(self._emit_solver_change)
		self.min_timestep_input.valueChanged.connect(self._emit_solver_change)
		self.max_time_input.valueChanged.connect(self._emit_solver_change)
		self.timestep_growth_factor_input.valueChanged.connect(self._emit_solver_change)
		self.timestep_shrink_factor_input.valueChanged.connect(self._emit_solver_change)
		self.max_step_retries_input.valueChanged.connect(self._emit_solver_change)
		self.max_newton_iterations_input.valueChanged.connect(self._emit_solver_change)
		self.residual_tolerance_input.valueChanged.connect(self._emit_solver_change)
		self.residual_norm_floor_input.valueChanged.connect(self._emit_solver_change)
		self.parameter_tolerance_input.valueChanged.connect(self._emit_solver_change)
		self.newton_pressure_damping_input.valueChanged.connect(self._emit_solver_change)
		self.newton_saturation_damping_input.valueChanged.connect(self._emit_solver_change)
		self.max_pressure_correction_input.valueChanged.connect(self._emit_solver_change)
		self.max_saturation_correction_input.valueChanged.connect(self._emit_solver_change)
		self.solver_preset_picker.currentIndexChanged.connect(self._apply_selected_preset)

	def set_project(self, project_config: ProjectConfig) -> None:
		blockers = [
			QSignalBlocker(self.name_input),
			QSignalBlocker(self.description_input),
			QSignalBlocker(self.case_name_input),
			QSignalBlocker(self.reference_pressure_input),
			QSignalBlocker(self.initial_timestep_input),
			QSignalBlocker(self.min_timestep_input),
			QSignalBlocker(self.max_time_input),
			QSignalBlocker(self.timestep_growth_factor_input),
			QSignalBlocker(self.timestep_shrink_factor_input),
			QSignalBlocker(self.max_step_retries_input),
			QSignalBlocker(self.max_newton_iterations_input),
			QSignalBlocker(self.residual_tolerance_input),
			QSignalBlocker(self.residual_norm_floor_input),
			QSignalBlocker(self.parameter_tolerance_input),
			QSignalBlocker(self.newton_pressure_damping_input),
			QSignalBlocker(self.newton_saturation_damping_input),
			QSignalBlocker(self.max_pressure_correction_input),
			QSignalBlocker(self.max_saturation_correction_input),
			QSignalBlocker(self.solver_preset_picker),
		]
		self.name_input.setText(project_config.name)
		self.description_input.setText(project_config.description)
		self.case_name_input.setText(project_config.run.case_name)
		self.reference_pressure_input.setValue(project_config.reference_data.reference_pressure)
		self.initial_timestep_input.setValue(project_config.solver.initial_timestep_days)
		self.min_timestep_input.setValue(project_config.solver.min_timestep_days)
		self.max_time_input.setValue(project_config.solver.max_time_days)
		self.timestep_growth_factor_input.setValue(project_config.solver.timestep_growth_factor)
		self.timestep_shrink_factor_input.setValue(project_config.solver.timestep_shrink_factor)
		self.max_step_retries_input.setValue(project_config.solver.max_step_retries)
		self.max_newton_iterations_input.setValue(project_config.solver.max_newton_iterations)
		self.residual_tolerance_input.setValue(project_config.solver.residual_tolerance)
		self.residual_norm_floor_input.setValue(project_config.solver.residual_norm_floor)
		self.parameter_tolerance_input.setValue(project_config.solver.parameter_tolerance)
		self.newton_pressure_damping_input.setValue(project_config.solver.newton_pressure_damping)
		self.newton_saturation_damping_input.setValue(project_config.solver.newton_saturation_damping)
		self.max_pressure_correction_input.setValue(project_config.solver.max_pressure_correction)
		self.max_saturation_correction_input.setValue(project_config.solver.max_saturation_correction)
		self.solver_preset_picker.setCurrentIndex(1)
		self.solver_preset_input.setText("Custom")
		del blockers

	def _apply_selected_preset(self, preset_index: int) -> None:
		preset_names = ["Stable", "Balanced", "Fast"]
		if preset_index < 0 or preset_index >= len(preset_names):
			return
		preset_name = preset_names[preset_index]
		preset = self.SOLVER_PRESETS[preset_name]
		blockers = [
			QSignalBlocker(self.timestep_growth_factor_input),
			QSignalBlocker(self.timestep_shrink_factor_input),
			QSignalBlocker(self.max_step_retries_input),
			QSignalBlocker(self.max_newton_iterations_input),
			QSignalBlocker(self.residual_tolerance_input),
			QSignalBlocker(self.residual_norm_floor_input),
			QSignalBlocker(self.newton_pressure_damping_input),
			QSignalBlocker(self.newton_saturation_damping_input),
			QSignalBlocker(self.max_pressure_correction_input),
			QSignalBlocker(self.max_saturation_correction_input),
		]
		self.timestep_growth_factor_input.setValue(float(preset["timestep_growth_factor"]))
		self.timestep_shrink_factor_input.setValue(float(preset["timestep_shrink_factor"]))
		self.max_step_retries_input.setValue(int(preset["max_step_retries"]))
		self.max_newton_iterations_input.setValue(int(preset["max_newton_iterations"]))
		self.residual_tolerance_input.setValue(float(preset["residual_tolerance"]))
		self.residual_norm_floor_input.setValue(float(preset["residual_norm_floor"]))
		self.newton_pressure_damping_input.setValue(float(preset["newton_pressure_damping"]))
		self.newton_saturation_damping_input.setValue(float(preset["newton_saturation_damping"]))
		self.max_pressure_correction_input.setValue(float(preset["max_pressure_correction"]))
		self.max_saturation_correction_input.setValue(float(preset["max_saturation_correction"]))
		del blockers
		self.solver_preset_input.setText(preset_name)
		self._emit_solver_change(mark_custom=False)

	def _emit_change(self) -> None:
		self.projectChanged.emit(
			self.name_input.text(),
			self.description_input.text(),
			self.case_name_input.text(),
			self.reference_pressure_input.value(),
		)

	def _emit_solver_change(self, *_args: object, mark_custom: bool = True) -> None:
		if mark_custom and self.solver_preset_input.text() != "Custom":
			self.solver_preset_input.setText("Custom")
		self.solverChanged.emit(
			self.initial_timestep_input.value(),
			self.min_timestep_input.value(),
			self.max_time_input.value(),
			self.timestep_growth_factor_input.value(),
			self.timestep_shrink_factor_input.value(),
			self.max_step_retries_input.value(),
			self.max_newton_iterations_input.value(),
			self.residual_tolerance_input.value(),
			self.residual_norm_floor_input.value(),
			self.parameter_tolerance_input.value(),
			self.newton_pressure_damping_input.value(),
			self.newton_saturation_damping_input.value(),
			self.max_pressure_correction_input.value(),
			self.max_saturation_correction_input.value(),
		)

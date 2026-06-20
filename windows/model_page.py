from __future__ import annotations

from PySide6.QtCore import QLocale, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import (
	QComboBox,
	QDoubleSpinBox,
	QFormLayout,
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QScrollArea,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from windows.ui_kit import SpinBoxInputBlocker, enable_precise_edit, make_card

# Decimal separator is fixed to "." regardless of OS locale so typed/pasted
# values always match what project files and scripts use (avoids "," vs "."
# ambiguity when copying numbers from JSON/config sources).
_NUMBER_LOCALE = QLocale(QLocale.Language.C)


def _form(parent: QWidget | None = None) -> QFormLayout:
	f = QFormLayout(parent)
	f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
	f.setHorizontalSpacing(14)
	f.setVerticalSpacing(8)
	f.setContentsMargins(10, 10, 10, 10)
	return f


class ScientificDoubleSpinBox(QDoubleSpinBox):
	"""Spin box for tiny threshold/tolerance values, displayed as e.g. "1.00e-05".

	Plain QDoubleSpinBox with fixed decimals is unreadable at this magnitude
	(0,0000100000) and the up/down arrows step by whole units. This displays
	scientific notation and steps by one order of magnitude per click.
	"""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("scientificSpinBox")
		self.setDecimals(15)
		self.setLocale(_NUMBER_LOCALE)

	def textFromValue(self, value: float) -> str:
		return f"{value:.2e}"

	def valueFromText(self, text: str) -> float:
		try:
			return float(text.strip())
		except ValueError:
			return self.value()

	def validate(self, text: str, pos: int):
		stripped = text.strip()
		if stripped in ("", "-", "+"):
			return (QValidator.State.Intermediate, text, pos)
		try:
			float(stripped)
			return (QValidator.State.Acceptable, text, pos)
		except ValueError:
			if all(ch in "0123456789.eE+-" for ch in stripped):
				return (QValidator.State.Intermediate, text, pos)
			return (QValidator.State.Invalid, text, pos)

	def stepBy(self, steps: int) -> None:
		current = self.value()
		if current <= 0.0:
			current = self.minimum() if self.minimum() > 0.0 else 1e-10
		self.setValue(current * (10.0 ** steps))


def _magnitude_spin(minimum: float, maximum: float, step: float = 1.0) -> QDoubleSpinBox:
	"""Real-world quantities (psi, etc.) — 2 decimals, consistent across the page."""
	box = QDoubleSpinBox()
	box.setDecimals(2)
	box.setRange(minimum, maximum)
	box.setSingleStep(step)
	box.setLocale(_NUMBER_LOCALE)
	return box


def _days_spin(minimum: float, maximum: float, step: float = 0.1) -> QDoubleSpinBox:
	"""Time durations in days — 4 decimals, consistent across the page."""
	box = QDoubleSpinBox()
	box.setDecimals(4)
	box.setRange(minimum, maximum)
	box.setSingleStep(step)
	box.setLocale(_NUMBER_LOCALE)
	return box


def _ratio_spin(minimum: float, maximum: float, step: float = 0.05) -> QDoubleSpinBox:
	"""Dimensionless 0-1 factors/dampings — 4 decimals, consistent across the page."""
	box = QDoubleSpinBox()
	box.setDecimals(4)
	box.setRange(minimum, maximum)
	box.setSingleStep(step)
	box.setLocale(_NUMBER_LOCALE)
	return box


def _tolerance_spin(minimum: float, maximum: float) -> ScientificDoubleSpinBox:
	"""Very small convergence thresholds — scientific notation, decade stepping."""
	box = ScientificDoubleSpinBox()
	box.setRange(minimum, maximum)
	return box


_PRESET_BADGE_STYLES: dict[str, tuple[str, str, str]] = {
	# preset_name: (background, text, border)
	"Custom": ("#f1f5f9", "#475569", "#cbd5e1"),
	"Stable": ("#ecfdf5", "#047857", "#a7f3d0"),
	"Balanced": ("#eff6ff", "#1d4ed8", "#bfdbfe"),
	"Fast": ("#fff7ed", "#c2410c", "#fed7aa"),
}


def _style_preset_badge(label: QLabel, preset_name: str) -> None:
	"""Render the active-preset indicator as a colored pill, not a text field.

	A QLineEdit here previously looked identical to the editable fields around
	it even though it only ever displays computed state — readers assumed it
	was an input. A pill makes "this is a status, not a field" visually clear.
	"""
	bg, fg, border = _PRESET_BADGE_STYLES.get(preset_name, _PRESET_BADGE_STYLES["Custom"])
	label.setText(preset_name)
	label.setStyleSheet(
		f"background-color: {bg}; color: {fg}; border: 1px solid {border};"
		"border-radius: 12px; padding: 5px 16px; font-weight: 700; font-size: 9pt;"
	)


def _stat_tile(caption: str, field: QWidget) -> QWidget:
	"""Caption-over-value tile, used instead of a full-width form row for read-out fields.

	A QFormLayout field column stretches to fill the row, which is why a value
	like "8" or "0.5000" used to sit inside a box as wide as the card. Sizing
	the field to its content and letting the tile's own layout clip it short
	removes that empty box without losing the label-above-value relationship.
	"""
	tile = QWidget()
	tile.setStyleSheet("background: transparent;")
	lay = QVBoxLayout(tile)
	lay.setContentsMargins(0, 0, 0, 0)
	lay.setSpacing(4)
	cap = QLabel(caption.upper())
	cap.setStyleSheet("font-size: 7.5pt; font-weight: 800; color: #94a3b8; letter-spacing: 0.4px;")
	lay.addWidget(cap)
	row = QHBoxLayout()
	row.setContentsMargins(0, 0, 0, 0)
	row.setSpacing(0)
	row.addWidget(field)
	row.addStretch(1)
	lay.addLayout(row)
	return tile


def _tile_grid(fields: list[tuple[str, QWidget]], ncols: int) -> QGridLayout:
	grid = QGridLayout()
	grid.setHorizontalSpacing(28)
	grid.setVerticalSpacing(18)
	for idx, (caption, field) in enumerate(fields):
		grid.addWidget(_stat_tile(caption, field), idx // ncols, idx % ncols)
	return grid


def _int_spin(minimum: int, maximum: int) -> QSpinBox:
	"""Integer-only counts — visually tagged so they're not mistaken for decimal fields."""
	box = QSpinBox()
	box.setRange(minimum, maximum)
	box.setObjectName("intSpinBox")
	box.setToolTip("Bilangan bulat — tidak menerima desimal.")
	box.setLocale(_NUMBER_LOCALE)
	return box


class ModelPage(QWidget):
	projectChanged = Signal(str, str, str)
	solverChanged = Signal(
		float, float, float, float, float, int, int,
		float, float, float, float, float, float, float, float,
	)
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

		outer = QVBoxLayout(self)
		outer.setSpacing(8)
		outer.setContentsMargins(14, 14, 14, 14)

		# ── Page header ───────────────────────────────────────────────
		hdr = QHBoxLayout()
		title = QLabel("Model & Solver")
		title.setObjectName("pageTitle")
		hdr.addWidget(title)
		hdr.addStretch()
		outer.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		outer.addWidget(sep)

		# ── Scroll container ──────────────────────────────────────────
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		inner = QWidget()
		col = QVBoxLayout(inner)
		col.setSpacing(12)
		col.setContentsMargins(0, 4, 4, 4)
		scroll.setWidget(inner)
		outer.addWidget(scroll, stretch=1)

		# ── Group: Project Info ───────────────────────────────────────
		card_proj, lay_proj = make_card("P", "#0891b2", "Project Info", "Identitas dan deskripsi project")
		frm_proj = _form()
		self.name_input = QLineEdit()
		self.description_input = QLineEdit()
		self.case_name_input = QLineEdit()
		frm_proj.addRow("Nama Project", self.name_input)
		frm_proj.addRow("Deskripsi", self.description_input)
		frm_proj.addRow("Nama Case", self.case_name_input)
		lay_proj.addLayout(frm_proj)
		col.addWidget(card_proj)

		self._spin_input_blockers: list[SpinBoxInputBlocker] = []

		# ── Group: Simulation Timing ──────────────────────────────────
		card_timing, lay_timing = make_card("T", "#2563eb", "Simulasi Timing", "Pengaturan waktu dan timestep")
		self.initial_timestep_input = _days_spin(0.0001, 3650.0)
		self.min_timestep_input = _days_spin(0.0001, 3650.0)
		self.min_timestep_input.setToolTip("Timestep terkecil yang masih diizinkan saat solver mengecilkan langkah waktu.")
		self.max_time_input = _days_spin(0.0001, 36500.0)
		lay_timing.addLayout(_tile_grid([
			("Timestep Awal (hari)", enable_precise_edit(self, self.initial_timestep_input, "Timestep Awal (hari)", self._spin_input_blockers)),
			("Timestep Minimum (hari)", enable_precise_edit(self, self.min_timestep_input, "Timestep Minimum (hari)", self._spin_input_blockers)),
			("Waktu Maks Simulasi (hari)", enable_precise_edit(self, self.max_time_input, "Waktu Maks Simulasi (hari)", self._spin_input_blockers)),
		], ncols=3))
		col.addWidget(card_timing)

		# ── Group: Solver Preset & Timestep Control ───────────────────
		card_preset, lay_preset = make_card("S", "#7c3aed", "Solver Preset & Kontrol Timestep", "Strategi adaptasi timestep")
		status_row = QHBoxLayout()
		status_row.setSpacing(10)
		status_label = QLabel("Preset Aktif")
		status_label.setStyleSheet("color: #475569; font-size: 9pt; font-weight: 600;")
		self.solver_preset_input = QLabel()
		_style_preset_badge(self.solver_preset_input, "Custom")
		self.solver_preset_picker = QComboBox()
		self.solver_preset_picker.addItems(["Stable", "Balanced", "Fast"])
		self.solver_preset_picker.setFixedWidth(140)
		self.solver_preset_apply_btn = QPushButton("Terapkan")
		self.solver_preset_apply_btn.setObjectName("btnSecondary")
		self.solver_preset_apply_btn.setToolTip(
			"Menimpa nilai Faktor Pertumbuhan/Penyusutan dt dan Maks Retry di bawah\n"
			"dengan nilai bawaan preset yang dipilih."
		)
		status_row.addWidget(status_label)
		status_row.addWidget(self.solver_preset_input)
		status_row.addStretch(1)
		status_row.addWidget(self.solver_preset_picker)
		status_row.addWidget(self.solver_preset_apply_btn)
		lay_preset.addLayout(status_row)
		self.timestep_growth_factor_input = _ratio_spin(1.0, 5.0)
		self.timestep_shrink_factor_input = _ratio_spin(0.05, 0.95)
		self.max_step_retries_input = _int_spin(0, 100)
		lay_preset.addLayout(_tile_grid([
			("Faktor Pertumbuhan dt", enable_precise_edit(self, self.timestep_growth_factor_input, "Faktor Pertumbuhan dt", self._spin_input_blockers)),
			("Faktor Penyusutan dt", enable_precise_edit(self, self.timestep_shrink_factor_input, "Faktor Penyusutan dt", self._spin_input_blockers)),
			("Maks Retry Timestep", enable_precise_edit(self, self.max_step_retries_input, "Maks Retry Timestep", self._spin_input_blockers)),
		], ncols=3))
		col.addWidget(card_preset)

		# ── Group: Newton Convergence ─────────────────────────────────
		card_newton, lay_newton = make_card("N", "#d97706", "Newton & Konvergensi", "Kriteria iterasi dan toleransi")
		self.max_newton_iterations_input = _int_spin(1, 200)
		self.residual_tolerance_input = _tolerance_spin(1e-10, 1.0)
		self.residual_tolerance_input.setToolTip(
			"Ambang residual absolut (dimensionless) untuk menyatakan Newton iteration konvergen."
		)
		self.residual_norm_floor_input = _ratio_spin(0.0001, 1.0, step=0.01)
		self.residual_norm_floor_input.setToolTip(
			"Batas bawah residual norm (dimensionless, relatif terhadap residual awal) — "
			"konvergensi tidak dipaksa lebih ketat dari nilai ini."
		)
		self.parameter_tolerance_pressure_input = _tolerance_spin(1e-10, 1000.0)
		self.parameter_tolerance_pressure_input.setToolTip(
			"Toleransi konvergensi untuk koreksi tekanan Δp, dalam psi."
		)
		self.parameter_tolerance_saturation_input = _tolerance_spin(1e-10, 1.0)
		self.parameter_tolerance_saturation_input.setToolTip(
			"Toleransi konvergensi untuk koreksi saturasi ΔS, sebagai fraksi (0–1)."
		)
		lay_newton.addLayout(_tile_grid([
			("Maks Iterasi Newton", enable_precise_edit(self, self.max_newton_iterations_input, "Maks Iterasi Newton", self._spin_input_blockers)),
			("Residual Tolerance", enable_precise_edit(self, self.residual_tolerance_input, "Residual Tolerance", self._spin_input_blockers)),
			("Residual Norm Floor (target)", enable_precise_edit(self, self.residual_norm_floor_input, "Residual Norm Floor (target)", self._spin_input_blockers)),
			("Parameter Tolerance Δp (psi)", enable_precise_edit(self, self.parameter_tolerance_pressure_input, "Parameter Tolerance Δp (psi)", self._spin_input_blockers)),
			("Parameter Tolerance ΔS (fraksi)", enable_precise_edit(self, self.parameter_tolerance_saturation_input, "Parameter Tolerance ΔS (fraksi)", self._spin_input_blockers)),
		], ncols=3))
		col.addWidget(card_newton)

		# ── Group: Damping & Correction Limits ───────────────────────
		card_damp, lay_damp = make_card("D", "#e11d48", "Damping & Batas Koreksi Newton", "Stabilisasi koreksi tiap iterasi")
		self.newton_pressure_damping_input = _ratio_spin(0.05, 1.0)
		self.newton_pressure_damping_input.setToolTip("Rentang valid: 0 < x ≤ 1. Nilai lebih kecil = koreksi per iterasi lebih halus.")
		self.newton_saturation_damping_input = _ratio_spin(0.05, 1.0)
		self.newton_saturation_damping_input.setToolTip("Rentang valid: 0 < x ≤ 1. Nilai lebih kecil = koreksi per iterasi lebih halus.")
		self.max_pressure_correction_input = _magnitude_spin(0.01, 1_000_000.0)
		self.max_saturation_correction_input = _ratio_spin(0.0001, 1.0, step=0.005)
		lay_damp.addLayout(_tile_grid([
			("Damping Tekanan", enable_precise_edit(self, self.newton_pressure_damping_input, "Damping Tekanan", self._spin_input_blockers)),
			("Damping Saturasi", enable_precise_edit(self, self.newton_saturation_damping_input, "Damping Saturasi", self._spin_input_blockers)),
			("Maks Koreksi ΔP (psi)", enable_precise_edit(self, self.max_pressure_correction_input, "Maks Koreksi ΔP (psi)", self._spin_input_blockers)),
			("Maks Koreksi ΔS", enable_precise_edit(self, self.max_saturation_correction_input, "Maks Koreksi ΔS", self._spin_input_blockers)),
		], ncols=2))
		col.addWidget(card_damp)

		col.addStretch()

		# ── Wire signals ──────────────────────────────────────────────
		self.name_input.editingFinished.connect(self._emit_change)
		self.description_input.editingFinished.connect(self._emit_change)
		self.case_name_input.editingFinished.connect(self._emit_change)
		self.initial_timestep_input.valueChanged.connect(self._emit_solver_change)
		self.min_timestep_input.valueChanged.connect(self._emit_solver_change)
		self.max_time_input.valueChanged.connect(self._emit_solver_change)
		self.timestep_growth_factor_input.valueChanged.connect(self._emit_solver_change)
		self.timestep_shrink_factor_input.valueChanged.connect(self._emit_solver_change)
		self.max_step_retries_input.valueChanged.connect(self._emit_solver_change)
		self.max_newton_iterations_input.valueChanged.connect(self._emit_solver_change)
		self.residual_tolerance_input.valueChanged.connect(self._emit_solver_change)
		self.residual_norm_floor_input.valueChanged.connect(self._emit_solver_change)
		self.parameter_tolerance_pressure_input.valueChanged.connect(self._emit_solver_change)
		self.parameter_tolerance_saturation_input.valueChanged.connect(self._emit_solver_change)
		self.newton_pressure_damping_input.valueChanged.connect(self._emit_solver_change)
		self.newton_saturation_damping_input.valueChanged.connect(self._emit_solver_change)
		self.max_pressure_correction_input.valueChanged.connect(self._emit_solver_change)
		self.max_saturation_correction_input.valueChanged.connect(self._emit_solver_change)
		self.solver_preset_apply_btn.clicked.connect(
			lambda: self._apply_selected_preset(self.solver_preset_picker.currentIndex())
		)

	def set_project(self, project_config: ProjectConfig) -> None:
		blockers = [
			QSignalBlocker(self.name_input),
			QSignalBlocker(self.description_input),
			QSignalBlocker(self.case_name_input),
			QSignalBlocker(self.initial_timestep_input),
			QSignalBlocker(self.min_timestep_input),
			QSignalBlocker(self.max_time_input),
			QSignalBlocker(self.timestep_growth_factor_input),
			QSignalBlocker(self.timestep_shrink_factor_input),
			QSignalBlocker(self.max_step_retries_input),
			QSignalBlocker(self.max_newton_iterations_input),
			QSignalBlocker(self.residual_tolerance_input),
			QSignalBlocker(self.residual_norm_floor_input),
			QSignalBlocker(self.parameter_tolerance_pressure_input),
			QSignalBlocker(self.parameter_tolerance_saturation_input),
			QSignalBlocker(self.newton_pressure_damping_input),
			QSignalBlocker(self.newton_saturation_damping_input),
			QSignalBlocker(self.max_pressure_correction_input),
			QSignalBlocker(self.max_saturation_correction_input),
			QSignalBlocker(self.solver_preset_picker),
		]
		self.name_input.setText(project_config.name)
		self.description_input.setText(project_config.description)
		self.case_name_input.setText(project_config.run.case_name)
		self.initial_timestep_input.setValue(project_config.solver.initial_timestep_days)
		self.min_timestep_input.setValue(project_config.solver.min_timestep_days)
		self.max_time_input.setValue(project_config.solver.max_time_days)
		self.timestep_growth_factor_input.setValue(project_config.solver.timestep_growth_factor)
		self.timestep_shrink_factor_input.setValue(project_config.solver.timestep_shrink_factor)
		self.max_step_retries_input.setValue(project_config.solver.max_step_retries)
		self.max_newton_iterations_input.setValue(project_config.solver.max_newton_iterations)
		self.residual_tolerance_input.setValue(project_config.solver.residual_tolerance)
		self.residual_norm_floor_input.setValue(project_config.solver.residual_norm_floor)
		self.parameter_tolerance_pressure_input.setValue(project_config.solver.parameter_tolerance_pressure)
		self.parameter_tolerance_saturation_input.setValue(project_config.solver.parameter_tolerance_saturation)
		self.newton_pressure_damping_input.setValue(project_config.solver.newton_pressure_damping)
		self.newton_saturation_damping_input.setValue(project_config.solver.newton_saturation_damping)
		self.max_pressure_correction_input.setValue(project_config.solver.max_pressure_correction)
		self.max_saturation_correction_input.setValue(project_config.solver.max_saturation_correction)
		self.solver_preset_picker.setCurrentIndex(1)
		_style_preset_badge(self.solver_preset_input, "Custom")
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
		_style_preset_badge(self.solver_preset_input, preset_name)
		self._emit_solver_change(mark_custom=False)

	def _emit_change(self) -> None:
		self.projectChanged.emit(
			self.name_input.text(),
			self.description_input.text(),
			self.case_name_input.text(),
		)

	def _emit_solver_change(self, *_args: object, mark_custom: bool = True) -> None:
		if mark_custom and self.solver_preset_input.text() != "Custom":
			_style_preset_badge(self.solver_preset_input, "Custom")
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
			self.parameter_tolerance_pressure_input.value(),
			self.parameter_tolerance_saturation_input.value(),
			self.newton_pressure_damping_input.value(),
			self.newton_saturation_damping_input.value(),
			self.max_pressure_correction_input.value(),
			self.max_saturation_correction_input.value(),
		)


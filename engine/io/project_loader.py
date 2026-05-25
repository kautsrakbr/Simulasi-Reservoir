from __future__ import annotations

import json
from pathlib import Path

from engine.domain.project import ProjectConfig
from engine.io.grid_reader import read_grid_spec
from engine.io.ref_reader import read_reference_data


def _as_float(value: object, default: float) -> float:
	if isinstance(value, (int, float)):
		return float(value)
	return default


def _as_int(value: object, default: int) -> int:
	if isinstance(value, int):
		return value
	if isinstance(value, float):
		return int(value)
	return default


def _as_bool(value: object, default: bool) -> bool:
	if isinstance(value, bool):
		return value
	return default


def _as_dict(value: object) -> dict[str, object]:
	if isinstance(value, dict):
		return {str(k): v for k, v in value.items()}
	return {}


def _deserialize_table(table_data: object) -> dict[str, list[tuple[float, float]]]:
	if not isinstance(table_data, dict):
		return {}

	result: dict[str, list[tuple[float, float]]] = {}
	for name, rows in table_data.items():
		if not isinstance(rows, list):
			continue
		parsed_rows: list[tuple[float, float]] = []
		for row in rows:
			if not isinstance(row, (list, tuple)) or len(row) < 2:
				continue
			x_value = _as_float(row[0], 0.0)
			y_value = _as_float(row[1], 0.0)
			parsed_rows.append((x_value, y_value))
		result[str(name)] = parsed_rows
	return result


def load_project(payload: dict[str, object]) -> ProjectConfig:
	project = ProjectConfig()
	project.name = str(payload.get("name", project.name))
	project.description = str(payload.get("description", project.description))

	reference_data_payload = _as_dict(payload.get("reference_data", {}))
	project.reference_data = read_reference_data(reference_data_payload)
	project.reference_data.reference_pressure = _as_float(
		reference_data_payload.get("reference_pressure"),
		project.reference_data.reference_pressure,
	)
	project.reference_data.oil_density_reference = _as_float(
		reference_data_payload.get("oil_density_reference"),
		project.reference_data.oil_density_reference,
	)
	project.reference_data.water_density_reference = _as_float(
		reference_data_payload.get("water_density_reference"),
		project.reference_data.water_density_reference,
	)
	project.reference_data.gas_density_reference = _as_float(
		reference_data_payload.get("gas_density_reference"),
		project.reference_data.gas_density_reference,
	)
	project.reference_data.rock_compressibility = _as_float(
		reference_data_payload.get("rock_compressibility"),
		project.reference_data.rock_compressibility,
	)
	project.reference_data.bubble_point_pressure = _as_float(
		reference_data_payload.get("bubble_point_pressure"),
		project.reference_data.bubble_point_pressure,
	)
	project.reference_data.oil_compressibility_reference = _as_float(
		reference_data_payload.get("oil_compressibility_reference"),
		project.reference_data.oil_compressibility_reference,
	)
	project.reference_data.water_compressibility_reference = _as_float(
		reference_data_payload.get("water_compressibility_reference"),
		project.reference_data.water_compressibility_reference,
	)
	project.reference_data.gas_compressibility_reference = _as_float(
		reference_data_payload.get("gas_compressibility_reference"),
		project.reference_data.gas_compressibility_reference,
	)

	grid_payload = _as_dict(payload.get("grid_spec", {}))
	project.grid_spec = read_grid_spec(grid_payload)

	solver_payload = _as_dict(payload.get("solver", {}))
	project.solver.initial_timestep_days = _as_float(
		solver_payload.get("initial_timestep_days"),
		project.solver.initial_timestep_days,
	)
	project.solver.min_timestep_days = _as_float(
		solver_payload.get("min_timestep_days"),
		project.solver.min_timestep_days,
	)
	project.solver.max_time_days = _as_float(
		solver_payload.get("max_time_days"),
		project.solver.max_time_days,
	)
	project.solver.timestep_growth_factor = _as_float(
		solver_payload.get("timestep_growth_factor"),
		project.solver.timestep_growth_factor,
	)
	project.solver.timestep_shrink_factor = _as_float(
		solver_payload.get("timestep_shrink_factor"),
		project.solver.timestep_shrink_factor,
	)
	project.solver.max_step_retries = _as_int(
		solver_payload.get("max_step_retries"),
		project.solver.max_step_retries,
	)
	project.solver.max_newton_iterations = _as_int(
		solver_payload.get("max_newton_iterations"),
		project.solver.max_newton_iterations,
	)
	project.solver.residual_tolerance = _as_float(
		solver_payload.get("residual_tolerance"),
		project.solver.residual_tolerance,
	)
	project.solver.parameter_tolerance = _as_float(
		solver_payload.get("parameter_tolerance"),
		project.solver.parameter_tolerance,
	)
	project.solver.residual_norm_floor = _as_float(
		solver_payload.get("residual_norm_floor"),
		project.solver.residual_norm_floor,
	)
	project.solver.newton_pressure_damping = _as_float(
		solver_payload.get("newton_pressure_damping"),
		project.solver.newton_pressure_damping,
	)
	project.solver.newton_saturation_damping = _as_float(
		solver_payload.get("newton_saturation_damping"),
		project.solver.newton_saturation_damping,
	)
	project.solver.max_pressure_correction = _as_float(
		solver_payload.get("max_pressure_correction"),
		project.solver.max_pressure_correction,
	)
	project.solver.max_saturation_correction = _as_float(
		solver_payload.get("max_saturation_correction"),
		project.solver.max_saturation_correction,
	)

	run_payload = _as_dict(payload.get("run", {}))
	project.run.case_name = str(run_payload.get("case_name", project.run.case_name))
	project.run.output_frequency = _as_int(
		run_payload.get("output_frequency"),
		project.run.output_frequency,
	)
	project.run.save_reports = _as_bool(
		run_payload.get("save_reports"),
		project.run.save_reports,
	)

	initial_payload = _as_dict(payload.get("initial_conditions", {}))
	project.initial_conditions.reference_depth = _as_float(
		initial_payload.get("reference_depth"),
		project.initial_conditions.reference_depth,
	)
	project.initial_conditions.initial_sw = _as_float(
		initial_payload.get("initial_sw"),
		project.initial_conditions.initial_sw,
	)
	project.initial_conditions.initial_sg = _as_float(
		initial_payload.get("initial_sg"),
		project.initial_conditions.initial_sg,
	)

	project.pvt_tables = _deserialize_table(payload.get("pvt_tables", {}))
	project.rock_tables = _deserialize_table(payload.get("rock_tables", {}))
	project.is_dirty = _as_bool(payload.get("is_dirty"), False)
	return project


def load_project_json(file_path: str | Path) -> ProjectConfig:
	source_path = Path(file_path)
	payload = json.loads(source_path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError("Format project JSON tidak valid.")
	return load_project({str(k): v for k, v in payload.items()})

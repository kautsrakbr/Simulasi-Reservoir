from __future__ import annotations

import json
from pathlib import Path

from engine.domain.project import ProjectConfig


def _serialize_table(table_data: dict[str, list[tuple[float, float]]]) -> dict[str, list[list[float]]]:
	return {
		name: [[float(x), float(y)] for x, y in points]
		for name, points in table_data.items()
	}


def write_project(project_config: ProjectConfig) -> dict[str, object]:
	return {
		"name": project_config.name,
		"description": project_config.description,
		"is_dirty": project_config.is_dirty,
		"reference_data": {
			"reference_depth": project_config.reference_data.reference_depth,
			"reference_pressure": project_config.reference_data.reference_pressure,
			"oil_density_reference": project_config.reference_data.oil_density_reference,
			"water_density_reference": project_config.reference_data.water_density_reference,
			"gas_density_reference": project_config.reference_data.gas_density_reference,
			"rock_compressibility": project_config.reference_data.rock_compressibility,
			"bubble_point_pressure": project_config.reference_data.bubble_point_pressure,
			"oil_compressibility_reference": project_config.reference_data.oil_compressibility_reference,
			"water_compressibility_reference": project_config.reference_data.water_compressibility_reference,
			"gas_compressibility_reference": project_config.reference_data.gas_compressibility_reference,
		},
		"solver": {
			"initial_timestep_days": project_config.solver.initial_timestep_days,
			"min_timestep_days": project_config.solver.min_timestep_days,
			"max_time_days": project_config.solver.max_time_days,
			"timestep_growth_factor": project_config.solver.timestep_growth_factor,
			"timestep_shrink_factor": project_config.solver.timestep_shrink_factor,
			"max_step_retries": project_config.solver.max_step_retries,
			"max_newton_iterations": project_config.solver.max_newton_iterations,
			"residual_tolerance": project_config.solver.residual_tolerance,
			"jacobian_refresh_interval": project_config.solver.jacobian_refresh_interval,
			"parameter_tolerance_pressure": project_config.solver.parameter_tolerance_pressure,
			"parameter_tolerance_saturation": project_config.solver.parameter_tolerance_saturation,
			"residual_norm_floor": project_config.solver.residual_norm_floor,
			"newton_pressure_damping": project_config.solver.newton_pressure_damping,
			"newton_saturation_damping": project_config.solver.newton_saturation_damping,
			"max_pressure_correction": project_config.solver.max_pressure_correction,
			"max_saturation_correction": project_config.solver.max_saturation_correction,
		},
		"run": {
			"case_name": project_config.run.case_name,
			"output_frequency": project_config.run.output_frequency,
			"save_reports": project_config.run.save_reports,
		},
		"initial_conditions": {
			"reference_depth": project_config.initial_conditions.reference_depth,
			"initial_sw": project_config.initial_conditions.initial_sw,
			"initial_sg": project_config.initial_conditions.initial_sg,
		},
		"grid_spec": {
			"nx": project_config.grid_spec.nx,
			"ny": project_config.grid_spec.ny,
			"nz": project_config.grid_spec.nz,
			"dx": project_config.grid_spec.dx,
			"dy": project_config.grid_spec.dy,
			"dz": project_config.grid_spec.dz,
			"connectivity": project_config.grid_spec.connectivity,
		},
		"constraints": {
			"grid_confirmed": project_config.constraints.grid_confirmed,
			"wells_confirmed": project_config.constraints.wells_confirmed,
			"perturbation_confirmed": project_config.constraints.perturbation_confirmed,
			"methods_confirmed": project_config.constraints.methods_confirmed,
		},
		"pvt_tables": _serialize_table(project_config.pvt_tables),
		"rock_tables": _serialize_table(project_config.rock_tables),
		"perturbation": {
			"perturbed_cell_id": project_config.perturbation.perturbed_cell_id,
			"delta_P":           project_config.perturbation.delta_P,
			"delta_Sw":          project_config.perturbation.delta_Sw,
			"delta_Sg":          project_config.perturbation.delta_Sg,
		},
		"methods": {
			"active_method": project_config.methods.active_method,
		},
		"wells": [
			{
				"name": w.name,
				"well_type": w.well_type,
				"cell_id": w.cell_id,
				"well_model": w.well_model,
				"flowrate": w.flowrate,
				"bhp": w.bhp,
				"wellbore_radius": w.wellbore_radius,
			}
			for w in project_config.wells
		],
	}


def write_project_json(project_config: ProjectConfig, file_path: str | Path) -> Path:
	target = Path(file_path)
	target.parent.mkdir(parents=True, exist_ok=True)
	payload = write_project(project_config)
	target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	return target

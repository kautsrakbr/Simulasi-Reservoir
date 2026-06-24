from __future__ import annotations

from engine.domain.project import ProjectConfig
from engine.domain.results import RunResult, TimeStepResult
from engine.domain.state import ReservoirState
from engine.grid.builder import build_grid
from engine.physics.flux import evaluate_cell_properties as _phase_properties
from engine.physics.wells import compute_well_index, compute_well_phase_rates
from engine.reporting.summary import build_run_summary
from engine.properties.pvt import interpolate_pvt
from engine.properties.relperm import interpolate_relperm


def get_run_summary(run_result: RunResult) -> dict[str, float | int | bool]:
	return build_run_summary(run_result)


def get_latest_step(run_result: RunResult) -> TimeStepResult | None:
	if not run_result.steps:
		return None
	return run_result.steps[-1]


def evaluate_cell_properties(project_config: ProjectConfig, p: float, sw: float, sg: float) -> dict[str, float]:
	"""
	Evaluates all PVT, rock-fluid, and derived properties for a cell under given conditions.
	This matches Step 7 in the Jupyter notebook but uses the project's dynamic tables.
	"""
	sw = max(0.0, min(1.0, sw))
	sg = max(0.0, min(1.0, sg))
	so = max(0.0, min(1.0, 1.0 - sw - sg))

	pvt = project_config.pvt_tables
	rock = project_config.rock_tables
	ref = project_config.reference_data

	# Interpolate PVT properties (using default values if tables are empty/missing)
	bo = interpolate_pvt(pvt["bo"], p) if pvt.get("bo") else 1.2
	bw = interpolate_pvt(pvt["bw"], p) if pvt.get("bw") else 1.0
	bg = interpolate_pvt(pvt["bg"], p) if pvt.get("bg") else 0.001
	mu_o = interpolate_pvt(pvt["mu_o"], p) if pvt.get("mu_o") else 1.4
	mu_w = interpolate_pvt(pvt["mu_w"], p) if pvt.get("mu_w") else 0.6
	mu_g = interpolate_pvt(pvt["mu_g"], p) if pvt.get("mu_g") else 0.02

	# Interpolate Rock-fluid properties
	kro = interpolate_relperm(rock["kro"], sw) if rock.get("kro") else max(0.0, 1.0 - sw)
	krw = interpolate_relperm(rock["krw"], sw) if rock.get("krw") else sw
	krg = interpolate_relperm(rock["krg"], sg) if rock.get("krg") else sg
	pcow = interpolate_relperm(rock["pcow"], sw) if rock.get("pcow") else 0.0
	pcgw = interpolate_relperm(rock["pcgw"], sg) if rock.get("pcgw") else 0.0

	# Reference densities
	rho_oil_ref = ref.oil_density_reference if ref.oil_density_reference > 0.0 else 50.0
	rho_water_ref = ref.water_density_reference if ref.water_density_reference > 0.0 else 62.4
	rho_gas_ref = ref.gas_density_reference if ref.gas_density_reference > 0.0 else 0.9

	# Densities under reservoir conditions
	rho_o = rho_oil_ref / bo if bo > 0.0 else rho_oil_ref
	rho_w = rho_water_ref / bw if bw > 0.0 else rho_water_ref
	rho_g = rho_gas_ref / bg if bg > 0.0 else rho_gas_ref

	# Mobilities
	lam_o = kro / mu_o if mu_o > 0.0 else 0.0
	lam_w = krw / mu_w if mu_w > 0.0 else 0.0
	lam_g = krg / mu_g if mu_g > 0.0 else 0.0

	return {
		"pressure_psia": p,
		"so": so,
		"sw": sw,
		"sg": sg,
		"bo": bo,
		"bw": bw,
		"bg": bg,
		"mu_o": mu_o,
		"mu_w": mu_w,
		"mu_g": mu_g,
		"kro": kro,
		"krw": krw,
		"krg": krg,
		"lam_o": lam_o,
		"lam_w": lam_w,
		"lam_g": lam_g,
		"rho_o": rho_o,
		"rho_w": rho_w,
		"rho_g": rho_g,
		"pcow": pcow,
		"pcgw": pcgw,
	}


def get_well_rates_per_step(project_config: ProjectConfig, run_result: RunResult) -> list[dict[str, float]]:
	"""Total field Qo/Qw/Qg (sum over all wells) at each saved timestep.

	Reuses engine.physics.wells.compute_well_phase_rates / compute_well_index
	-- the exact same per-well rate formulas the solver applies internally --
	so the Result tab's numbers always match what actually drove the run,
	rather than a second, possibly-diverging approximation.
	"""
	try:
		grid_model = build_grid(project_config)
	except Exception:
		grid_model = None

	rows: list[dict[str, float]] = []
	for step_idx, step in enumerate(run_result.steps, start=1):
		state = ReservoirState(pressure=step.pressure, sw=step.sw, sg=step.sg)
		qo_total = qw_total = qg_total = 0.0
		for well in project_config.wells:
			cell_index = well.cell_id - 1
			if cell_index < 0 or cell_index >= len(state.pressure):
				continue
			cell_props = _phase_properties(
				cell_index, state, project_config.reference_data,
				project_config.pvt_tables, project_config.rock_tables,
			)
			if well.well_model == "peaceman" and grid_model is not None and cell_index < len(grid_model.cells):
				well_index = compute_well_index(grid_model.cells[cell_index], grid_model.spec, well.wellbore_radius)
				rates = compute_well_phase_rates(
					well, cell_props, cell_pressure=state.pressure[cell_index], well_index=well_index,
				)
			else:
				rates = compute_well_phase_rates(well, cell_props)
			qo_total += rates.oil
			qw_total += rates.water
			qg_total += rates.gas
		rows.append({
			"step": step_idx,
			"time_days": step.summary.time_days,
			"qo": qo_total,
			"qw": qw_total,
			"qg": qg_total,
		})
	return rows


def get_all_cell_properties(project_config: ProjectConfig, step_result: TimeStepResult) -> list[dict[str, float]]:
	"""
	Returns evaluated properties for all cells in a timestep step_result.
	"""
	n_cells = len(step_result.pressure)
	results = []
	for i in range(n_cells):
		p = step_result.pressure[i]
		sw = step_result.sw[i]
		sg = step_result.sg[i]
		props = evaluate_cell_properties(project_config, p, sw, sg)
		props["cell"] = i + 1
		# Add spatial indexing
		nx = project_config.grid_spec.nx
		row, col = divmod(i, nx)
		props["i_index"] = col
		props["j_index"] = row
		results.append(props)
	return results

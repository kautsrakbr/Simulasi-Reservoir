from __future__ import annotations

from engine.domain.grid import CellData, GridModel
from engine.domain.project import ReferenceData
from engine.domain.state import ReservoirState
from engine.properties.pvt import interpolate_pvt


def _safe_div(value: float, denominator: float, fallback: float = 1.0) -> float:
	if abs(denominator) < 1e-12:
		return value / fallback
	return value / denominator


def _clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def _evaluate_b_factor(
	table_name: str,
	pressure: float,
	pvt_tables: dict[str, list[tuple[float, float]]],
	default_value: float,
) -> float:
	table = pvt_tables.get(table_name)
	if not table:
		return default_value
	return interpolate_pvt(table, pressure)


def compute_effective_pore_volume(cell: CellData, pressure: float, reference_data: ReferenceData) -> float:
	porosity = cell.porosity if cell.porosity > 0.0 else 0.2
	scale = 1.0 + reference_data.rock_compressibility * (pressure - reference_data.reference_pressure)
	scale = max(scale, 0.0)
	return cell.bulk_volume * porosity * scale


def compute_oil_accumulation(
	pv_k: float,
	so_k: float,
	bo_k: float,
	pv_n: float,
	so_n: float,
	bo_n: float,
	dt_days: float,
) -> float:
	current = _safe_div(pv_k * so_k, bo_k)
	previous = _safe_div(pv_n * so_n, bo_n)
	return (current - previous) / dt_days


def compute_water_accumulation(
	pv_k: float,
	sw_k: float,
	bw_k: float,
	pv_n: float,
	sw_n: float,
	bw_n: float,
	dt_days: float,
) -> float:
	current = _safe_div(pv_k * sw_k, bw_k)
	previous = _safe_div(pv_n * sw_n, bw_n)
	return (current - previous) / dt_days


def compute_gas_accumulation(
	pv_k: float,
	sg_k: float,
	bg_k: float,
	pv_n: float,
	sg_n: float,
	bg_n: float,
	dt_days: float,
) -> float:
	current = _safe_div(pv_k * sg_k, bg_k)
	previous = _safe_div(pv_n * sg_n, bg_n)
	return (current - previous) / dt_days


def assemble_accumulation_terms(
	grid_model: GridModel,
	state_n: ReservoirState,
	state_k: ReservoirState,
	reference_data: ReferenceData,
	pvt_tables: dict[str, list[tuple[float, float]]],
	dt_days: float,
) -> dict[str, list[float]]:
	dt = dt_days if dt_days > 1e-12 else 1e-12

	oil_accumulation: list[float] = []
	water_accumulation: list[float] = []
	gas_accumulation: list[float] = []
	total_accumulation: list[float] = []

	for index, cell in enumerate(grid_model.cells):
		pressure_n = state_n.pressure[index]
		pressure_k = state_k.pressure[index]

		sw_n = _clamp(state_n.sw[index], 0.0, 1.0)
		sg_n = _clamp(state_n.sg[index], 0.0, 1.0)
		sw_k = _clamp(state_k.sw[index], 0.0, 1.0)
		sg_k = _clamp(state_k.sg[index], 0.0, 1.0)

		so_n = _clamp(1.0 - sw_n - sg_n, 0.0, 1.0)
		so_k = _clamp(1.0 - sw_k - sg_k, 0.0, 1.0)

		pv_n = compute_effective_pore_volume(cell, pressure_n, reference_data)
		pv_k = compute_effective_pore_volume(cell, pressure_k, reference_data)

		bo_n = _evaluate_b_factor("bo", pressure_n, pvt_tables, 1.0)
		bo_k = _evaluate_b_factor("bo", pressure_k, pvt_tables, 1.0)
		bw_n = _evaluate_b_factor("bw", pressure_n, pvt_tables, 1.0)
		bw_k = _evaluate_b_factor("bw", pressure_k, pvt_tables, 1.0)
		bg_n = _evaluate_b_factor("bg", pressure_n, pvt_tables, 1.0)
		bg_k = _evaluate_b_factor("bg", pressure_k, pvt_tables, 1.0)

		oil_value = compute_oil_accumulation(pv_k, so_k, bo_k, pv_n, so_n, bo_n, dt)
		water_value = compute_water_accumulation(pv_k, sw_k, bw_k, pv_n, sw_n, bw_n, dt)
		gas_value = compute_gas_accumulation(pv_k, sg_k, bg_k, pv_n, sg_n, bg_n, dt)
		total_value = oil_value + water_value + gas_value

		oil_accumulation.append(oil_value)
		water_accumulation.append(water_value)
		gas_accumulation.append(gas_value)
		total_accumulation.append(total_value)

	return {
		"oil": oil_accumulation,
		"water": water_accumulation,
		"gas": gas_accumulation,
		"total": total_accumulation,
	}

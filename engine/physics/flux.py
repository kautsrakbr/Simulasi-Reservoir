from __future__ import annotations

from dataclasses import dataclass

from engine.domain.grid import Connection, GridModel
from engine.domain.project import ReferenceData
from engine.domain.state import ReservoirState
from engine.physics.potential import compute_gas_potential, compute_oil_potential, compute_water_potential
from engine.properties.pvt import interpolate_pvt
from engine.properties.relperm import interpolate_relperm


@dataclass(slots=True)
class _CellPhaseProperties:
	bo: float
	bw: float
	bg: float
	mobility_oil: float
	mobility_water: float
	mobility_gas: float
	density_oil: float
	density_water: float
	density_gas: float
	pcow: float
	pcgw: float


def _clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def _safe_div(value: float, denominator: float, fallback: float = 0.0) -> float:
	if abs(denominator) < 1e-12:
		return fallback
	return value / denominator


def _read_reference_density(reference_data: ReferenceData | dict[str, float] | object, attr: str, default: float) -> float:
	value: object
	if isinstance(reference_data, dict):
		value = reference_data.get(attr, default)
	else:
		value = getattr(reference_data, attr, default)
	if isinstance(value, (int, float)):
		return float(value) if float(value) > 0.0 else default
	return default


def _evaluate_pvt(
	table_name: str,
	pressure: float,
	pvt_tables: dict[str, list[tuple[float, float]]],
	default_value: float,
) -> float:
	table = pvt_tables.get(table_name)
	if not table:
		return default_value
	return interpolate_pvt(table, pressure)


def _evaluate_rock(
	table_name: str,
	saturation: float,
	rock_tables: dict[str, list[tuple[float, float]]],
	default_value: float,
) -> float:
	table = rock_tables.get(table_name)
	if not table:
		return default_value
	return interpolate_relperm(table, saturation)


def _evaluate_cell_properties(
	cell_index: int,
	state: ReservoirState,
	reference_data: ReferenceData | dict[str, float] | object,
	pvt_tables: dict[str, list[tuple[float, float]]],
	rock_tables: dict[str, list[tuple[float, float]]],
) -> _CellPhaseProperties:
	pressure = state.pressure[cell_index]
	sw = _clamp(state.sw[cell_index], 0.0, 1.0)
	sg = _clamp(state.sg[cell_index], 0.0, 1.0)
	so = _clamp(1.0 - sw - sg, 0.0, 1.0)

	bo = _evaluate_pvt("bo", pressure, pvt_tables, 1.0)
	bw = _evaluate_pvt("bw", pressure, pvt_tables, 1.0)
	bg = _evaluate_pvt("bg", pressure, pvt_tables, 1.0)
	mu_o = _evaluate_pvt("mu_o", pressure, pvt_tables, 2.0)
	mu_w = _evaluate_pvt("mu_w", pressure, pvt_tables, 1.0)
	mu_g = _evaluate_pvt("mu_g", pressure, pvt_tables, 0.02)

	kro = _evaluate_rock("kro", sw, rock_tables, max(0.0, 1.0 - sw))
	krw = _evaluate_rock("krw", sw, rock_tables, sw)
	krg = _evaluate_rock("krg", sg, rock_tables, sg)
	pcow = _evaluate_rock("pcow", sw, rock_tables, 0.0)
	pcgw = _evaluate_rock("pcgw", sg, rock_tables, 0.0)

	oil_density_ref = _read_reference_density(reference_data, "oil_density_reference", 0.8)
	water_density_ref = _read_reference_density(reference_data, "water_density_reference", 1.0)
	gas_density_ref = _read_reference_density(reference_data, "gas_density_reference", 0.06)

	density_oil = _safe_div(oil_density_ref, bo, oil_density_ref)
	density_water = _safe_div(water_density_ref, bw, water_density_ref)
	density_gas = _safe_div(gas_density_ref, bg, gas_density_ref)

	mobility_oil = _safe_div(kro, mu_o, 0.0)
	mobility_water = _safe_div(krw, mu_w, 0.0)
	mobility_gas = _safe_div(krg, mu_g, 0.0)

	return _CellPhaseProperties(
		bo=bo,
		bw=bw,
		bg=bg,
		mobility_oil=mobility_oil,
		mobility_water=mobility_water,
		mobility_gas=mobility_gas,
		density_oil=density_oil,
		density_water=density_water,
		density_gas=density_gas,
		pcow=pcow,
		pcgw=pcgw,
	)


def _build_upwind_props(
	phase: str,
	potential: float,
	from_props: _CellPhaseProperties,
	to_props: _CellPhaseProperties,
) -> dict[str, float]:
	upstream = from_props if potential <= 0.0 else to_props
	if phase == "oil":
		b_avg = 0.5 * (from_props.bo + to_props.bo)
		mobility = upstream.mobility_oil
	elif phase == "water":
		b_avg = 0.5 * (from_props.bw + to_props.bw)
		mobility = upstream.mobility_water
	else:
		b_avg = 0.5 * (from_props.bg + to_props.bg)
		mobility = upstream.mobility_gas
	return {
		"mobility": mobility,
		"b_avg": b_avg,
	}


def _compute_phase_flux(connection: Connection, upwind_props: object, potential: float) -> float:
	mobility = _read_mobility(upwind_props)
	b_avg = _read_volume_factor(upwind_props)
	if connection.transmissibility <= 0.0:
		return 0.0
	# Sign convention: positive value means outflow from connection.from_cell_id.
	return -connection.transmissibility * mobility * potential / b_avg


def compute_oil_flux(connection: Connection, upwind_props: object, potential: float) -> float:
	return _compute_phase_flux(connection, upwind_props, potential)


def compute_water_flux(connection: Connection, upwind_props: object, potential: float) -> float:
	return _compute_phase_flux(connection, upwind_props, potential)


def compute_gas_flux(connection: Connection, upwind_props: object, potential: float) -> float:
	return _compute_phase_flux(connection, upwind_props, potential)


def assemble_flux_terms(cell_index: int, grid_model: object, state: object, properties: object) -> dict[str, float]:
	if not isinstance(grid_model, GridModel):
		raise TypeError("grid_model harus berupa GridModel.")
	if not isinstance(state, ReservoirState):
		raise TypeError("state harus berupa ReservoirState.")
	if not isinstance(properties, dict):
		raise TypeError("properties harus berupa dict.")
	if cell_index < 0 or cell_index >= len(grid_model.cells):
		raise IndexError("cell_index di luar rentang grid.")

	reference_data = properties.get("reference_data", ReferenceData())
	pvt_tables = properties.get("pvt_tables", {})
	rock_tables = properties.get("rock_tables", {})
	if not isinstance(pvt_tables, dict):
		pvt_tables = {}
	if not isinstance(rock_tables, dict):
		rock_tables = {}

	phase_connection_fluxes = compute_phase_connection_fluxes(
		grid_model,
		state,
		reference_data=reference_data,
		pvt_tables=pvt_tables,
		rock_tables=rock_tables,
	)
	phase_net_flux = compute_phase_net_flux_per_cell(grid_model, phase_connection_fluxes)
	oil_flux = phase_net_flux["oil"][cell_index]
	water_flux = phase_net_flux["water"][cell_index]
	gas_flux = phase_net_flux["gas"][cell_index]
	return {
		"oil": oil_flux,
		"water": water_flux,
		"gas": gas_flux,
		"total": oil_flux + water_flux + gas_flux,
	}


def compute_phase_connection_fluxes(
	grid_model: GridModel,
	state: ReservoirState,
	*,
	reference_data: ReferenceData | dict[str, float] | object,
	pvt_tables: dict[str, list[tuple[float, float]]],
	rock_tables: dict[str, list[tuple[float, float]]],
) -> dict[str, list[float]]:
	cell_properties = [
		_evaluate_cell_properties(index, state, reference_data, pvt_tables, rock_tables)
		for index, _ in enumerate(grid_model.cells)
	]

	oil_fluxes: list[float] = []
	water_fluxes: list[float] = []
	gas_fluxes: list[float] = []

	for connection in grid_model.connections:
		from_index = connection.from_cell_id
		to_index = connection.to_cell_id
		from_cell = grid_model.cells[from_index]
		to_cell = grid_model.cells[to_index]
		from_props = cell_properties[from_index]
		to_props = cell_properties[to_index]

		delta_depth = to_cell.depth - from_cell.depth
		oil_potential = compute_oil_potential(
			state.pressure[from_index],
			state.pressure[to_index],
			from_props.density_oil,
			to_props.density_oil,
			delta_depth,
		)
		water_potential = compute_water_potential(
			state.pressure[from_index],
			state.pressure[to_index],
			from_props.density_water,
			to_props.density_water,
			delta_depth,
			from_props.pcow,
			to_props.pcow,
		)
		gas_potential = compute_gas_potential(
			state.pressure[from_index],
			state.pressure[to_index],
			from_props.density_gas,
			to_props.density_gas,
			delta_depth,
			from_props.pcgw,
			to_props.pcgw,
		)

		oil_fluxes.append(
			compute_oil_flux(connection, _build_upwind_props("oil", oil_potential, from_props, to_props), oil_potential)
		)
		water_fluxes.append(
			compute_water_flux(
				connection,
				_build_upwind_props("water", water_potential, from_props, to_props),
				water_potential,
			)
		)
		gas_fluxes.append(
			compute_gas_flux(connection, _build_upwind_props("gas", gas_potential, from_props, to_props), gas_potential)
		)

	return {
		"oil": oil_fluxes,
		"water": water_fluxes,
		"gas": gas_fluxes,
	}


def compute_phase_net_flux_per_cell(
	grid_model: GridModel,
	phase_connection_fluxes: dict[str, list[float]],
) -> dict[str, list[float]]:
	return {
		"oil": compute_net_flux_per_cell(grid_model, phase_connection_fluxes.get("oil", [])),
		"water": compute_net_flux_per_cell(grid_model, phase_connection_fluxes.get("water", [])),
		"gas": compute_net_flux_per_cell(grid_model, phase_connection_fluxes.get("gas", [])),
	}


def compute_connection_fluxes(grid_model: GridModel, pressure: list[float]) -> list[float]:
	fluxes: list[float] = []
	for connection in grid_model.connections:
		from_pressure = pressure[connection.from_cell_id]
		to_pressure = pressure[connection.to_cell_id]
		potential = from_pressure - to_pressure
		fluxes.append(connection.transmissibility * potential)
	return fluxes


def compute_net_flux_per_cell(grid_model: GridModel, connection_fluxes: list[float]) -> list[float]:
	net_flux = [0.0 for _ in grid_model.cells]
	for connection, flux in zip(grid_model.connections, connection_fluxes):
		net_flux[connection.from_cell_id] -= flux
		net_flux[connection.to_cell_id] += flux
	return net_flux


def _read_mobility(upwind_props: object) -> float:
	if isinstance(upwind_props, dict):
		value = upwind_props.get("mobility", 1.0)
		if isinstance(value, (int, float)):
			return float(value)
	return 1.0


def _read_volume_factor(upwind_props: object) -> float:
	if isinstance(upwind_props, dict):
		value = upwind_props.get("b_avg", upwind_props.get("volume_factor", 1.0))
		if isinstance(value, (int, float)):
			return max(float(value), 1e-12)
	return 1.0

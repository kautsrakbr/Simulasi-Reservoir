from __future__ import annotations

import math
from dataclasses import dataclass

from engine.common.constants import TRANSMISSIBILITY_UNIT_FACTOR
from engine.domain.grid import CellData, GridModel, GridSpec
from engine.domain.project import WellConfig
from engine.physics.flux import CellPhaseProperties


@dataclass(slots=True)
class WellPhaseRates:
	oil: float = 0.0
	water: float = 0.0
	gas: float = 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
	if abs(denominator) < 1e-12:
		return 0.0
	return numerator / denominator


def compute_well_index(cell: CellData, grid_spec: GridSpec, wellbore_radius: float) -> float:
	"""Peaceman well index, WI = 2*pi*k*h / ln(re/rw) (docs/rumuspenting.md §4).

	k is the geometric mean of kx/ky (radial flow converges in the x-y plane
	toward a vertical well) and h is the cell thickness (dz). re is the
	isotropic Peaceman equivalent radius re = 0.14*sqrt(dx^2 + dy^2) for a
	well centred in a single grid cell. The same field-unit conversion factor
	used for inter-cell transmissibility is reused here so WI stays on the
	same unit system as the rest of this simulator's Darcy terms.
	"""
	k_eff = math.sqrt(max(cell.perm_x, 0.0) * max(cell.perm_y, 0.0))
	h = max(grid_spec.dz, 0.0)
	rw = max(wellbore_radius, 1e-6)
	re = 0.14 * math.sqrt(grid_spec.dx ** 2 + grid_spec.dy ** 2)
	if k_eff <= 0.0 or h <= 0.0 or re <= rw:
		return 0.0
	return TRANSMISSIBILITY_UNIT_FACTOR * 2.0 * math.pi * k_eff * h / math.log(re / rw)


def compute_well_phase_rates(
	well: WellConfig,
	cell_props: CellPhaseProperties,
	*,
	cell_pressure: float = 0.0,
	well_index: float = 0.0,
) -> WellPhaseRates:
	"""Well source/sink phase rates for the cell `well` is completed in.

	Two models (docs/rumuspenting.md §4), selected via `well.well_model`:

	- "peaceman": rate-from-pressure model, qo = WI * Mo * (p_cell - p_wf),
	  qw = WI * Mw * (p_cell - p_wf), qg = WI * Mg * (p_cell - p_wf) + Rso*qo.
	  `well_index` and `cell_pressure` must be supplied by the caller.
	- "simple_flowrate" (default): `well.flowrate` is read directly as the
	  oil-equivalent rate (STB/day); water/gas are allocated via the
	  *mobility ratio* at the well cell -- qw/qo = Mw/Mo and
	  qg_free/qo = Mg/Mo -- which is exactly the ratio the Peaceman formulas
	  above imply (WI and Δp cancel out of the ratio).

	Sign convention: positive = withdrawal from the cell (production),
	negative = addition to the cell (injection).
	"""
	if well.well_model == "peaceman":
		delta_p = cell_pressure - well.bhp
		qo = well_index * cell_props.mobility_oil * delta_p
		qw = well_index * cell_props.mobility_water * delta_p
		qg = well_index * cell_props.mobility_gas * delta_p + cell_props.rso * qo
		return WellPhaseRates(oil=qo, water=qw, gas=qg)

	sign = 1.0 if well.well_type == "production" else -1.0
	qo = sign * well.flowrate
	qw = qo * _safe_ratio(cell_props.mobility_water, cell_props.mobility_oil)
	qg = qo * _safe_ratio(cell_props.mobility_gas, cell_props.mobility_oil) + cell_props.rso * qo
	return WellPhaseRates(oil=qo, water=qw, gas=qg)


def assemble_well_terms(
	wells: list[WellConfig],
	cell_properties: list[CellPhaseProperties],
	grid_model: GridModel,
	pressure: list[float],
) -> dict[str, list[float]]:
	"""Per-cell oil/water/gas well source-sink terms, 0-indexed like grid cells.

	docs/rumuspenting.md §5 only subtracts qo and qg from the oil/gas residuals
	("qo dan qg hanya ada di cell sumur") -- water has no well residual term, so
	the water rate here is for diagnostics/display only.
	"""
	cell_count = len(cell_properties)
	oil = [0.0] * cell_count
	water = [0.0] * cell_count
	gas = [0.0] * cell_count

	for well in wells:
		cell_index = well.cell_id - 1
		if cell_index < 0 or cell_index >= cell_count:
			continue
		if well.well_model == "peaceman" and cell_index < len(grid_model.cells):
			well_index = compute_well_index(grid_model.cells[cell_index], grid_model.spec, well.wellbore_radius)
			cell_pressure = pressure[cell_index] if cell_index < len(pressure) else 0.0
			rates = compute_well_phase_rates(
				well, cell_properties[cell_index],
				cell_pressure=cell_pressure, well_index=well_index,
			)
		else:
			rates = compute_well_phase_rates(well, cell_properties[cell_index])
		oil[cell_index] += rates.oil
		water[cell_index] += rates.water
		gas[cell_index] += rates.gas

	return {"oil": oil, "water": water, "gas": gas}

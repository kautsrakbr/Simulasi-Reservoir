from __future__ import annotations


def compute_oil_potential(
	pressure_from: float,
	pressure_to: float,
	density_from: float,
	density_to: float,
	delta_depth: float,
) -> float:
	average_density = 0.5 * (density_from + density_to)
	gravity_term = average_density * delta_depth / 144.0
	return pressure_to - pressure_from - gravity_term


def compute_water_potential(
	pressure_from: float,
	pressure_to: float,
	density_from: float,
	density_to: float,
	delta_depth: float,
	pcow_from: float,
	pcow_to: float,
) -> float:
	average_density = 0.5 * (density_from + density_to)
	gravity_term = average_density * delta_depth / 144.0
	capillary_term = pcow_to - pcow_from
	return pressure_to - pressure_from - gravity_term - capillary_term


def compute_gas_potential(
	pressure_from: float,
	pressure_to: float,
	density_from: float,
	density_to: float,
	delta_depth: float,
	pcgw_from: float,
	pcgw_to: float,
) -> float:
	average_density = 0.5 * (density_from + density_to)
	gravity_term = average_density * delta_depth / 144.0
	capillary_term = pcgw_to - pcgw_from
	return pressure_to - pressure_from - gravity_term + capillary_term

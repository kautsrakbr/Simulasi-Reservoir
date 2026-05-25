from __future__ import annotations


def compute_oil_flux(connection: object, upwind_props: object, potential: float) -> float:
	del connection, upwind_props, potential
	raise NotImplementedError("Oil flux belum diimplementasikan.")


def compute_water_flux(connection: object, upwind_props: object, potential: float) -> float:
	del connection, upwind_props, potential
	raise NotImplementedError("Water flux belum diimplementasikan.")


def compute_gas_flux(connection: object, upwind_props: object, potential: float) -> float:
	del connection, upwind_props, potential
	raise NotImplementedError("Gas flux belum diimplementasikan.")


def assemble_flux_terms(cell_index: int, grid_model: object, state: object, properties: object) -> dict[str, float]:
	del cell_index, grid_model, state, properties
	raise NotImplementedError("Assembly flux terms belum diimplementasikan.")

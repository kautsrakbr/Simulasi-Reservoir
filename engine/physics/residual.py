from __future__ import annotations


def assemble_cell_residual(net_flux: float, accumulation: float, well_term: float = 0.0) -> float:
	return net_flux - accumulation - well_term


def assemble_full_residual(
	net_flux_per_cell: list[float],
	accumulation_per_cell: list[float],
	well_term_per_cell: list[float] | None = None,
) -> list[float]:
	residual: list[float] = []
	for index, net_flux in enumerate(net_flux_per_cell):
		accumulation = accumulation_per_cell[index] if index < len(accumulation_per_cell) else 0.0
		well_term = well_term_per_cell[index] if well_term_per_cell is not None and index < len(well_term_per_cell) else 0.0
		residual.append(assemble_cell_residual(net_flux, accumulation, well_term))
	return residual


def residual_max_abs(residual: list[float]) -> float:
	return max((abs(value) for value in residual), default=0.0)

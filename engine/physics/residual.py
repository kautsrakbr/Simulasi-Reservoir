from __future__ import annotations


def assemble_cell_residual(net_flux: float, accumulation: float) -> float:
	return net_flux - accumulation


def assemble_full_residual(net_flux_per_cell: list[float], accumulation_per_cell: list[float]) -> list[float]:
	residual: list[float] = []
	for index, net_flux in enumerate(net_flux_per_cell):
		accumulation = accumulation_per_cell[index] if index < len(accumulation_per_cell) else 0.0
		residual.append(assemble_cell_residual(net_flux, accumulation))
	return residual


def residual_max_abs(residual: list[float]) -> float:
	return max((abs(value) for value in residual), default=0.0)

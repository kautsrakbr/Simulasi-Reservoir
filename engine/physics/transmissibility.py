from __future__ import annotations

from engine.common.constants import TRANSMISSIBILITY_UNIT_FACTOR


def compute_harmonic_permeability(k1: float, k2: float) -> float:
	if k1 <= 0.0 or k2 <= 0.0:
		return 0.0
	return 2.0 * k1 * k2 / (k1 + k2)


def compute_transmissibility(
	k1: float,
	k2: float,
	area: float,
	distance: float,
	unit_factor: float = TRANSMISSIBILITY_UNIT_FACTOR,
) -> float:
	if distance <= 0.0:
		return 0.0
	return unit_factor * compute_harmonic_permeability(k1, k2) * area / distance

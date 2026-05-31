from __future__ import annotations

"""Perhitungan densitas in-situ fluida reservoir.

Densitas in-situ dihitung dari densitas referensi permukaan dibagi formation
volume factor: ρ_res = ρ_surface / B.  Ini konsisten dengan cara flux.py dan
accumulation.py menggunakan densitas, dan sesuai konvensi workbook VBA.
"""


def compute_oil_density(oil_density_ref: float, bo: float) -> float:
	"""Hitung densitas oil di kondisi reservoir (lb/ft³ atau g/cc, tergantung satuan ρ_ref).

	Formula: ρ_o = ρ_o_ref / B_o

	Args:
		oil_density_ref: Densitas oil di kondisi permukaan (lb/ft³ atau g/cc).
		bo: Formation volume factor oil (RB/STB). Harus > 0.

	Returns:
		Densitas in-situ (satuan sama dengan ρ_ref).
	"""
	if bo <= 0.0:
		return oil_density_ref
	return oil_density_ref / bo


def compute_water_density(water_density_ref: float, bw: float) -> float:
	"""Hitung densitas air di kondisi reservoir.

	Formula: ρ_w = ρ_w_ref / B_w

	Args:
		water_density_ref: Densitas air di kondisi permukaan.
		bw: Formation volume factor air (RB/STB). Harus > 0.

	Returns:
		Densitas in-situ.
	"""
	if bw <= 0.0:
		return water_density_ref
	return water_density_ref / bw


def compute_gas_density(gas_density_ref: float, bg: float) -> float:
	"""Hitung densitas gas di kondisi reservoir.

	Formula: ρ_g = ρ_g_ref / B_g

	Args:
		gas_density_ref: Densitas gas di kondisi permukaan (lb/ft³ atau g/cc).
		bg: Formation volume factor gas (RB/Mscf). Harus > 0.

	Returns:
		Densitas in-situ.
	"""
	if bg <= 0.0:
		return gas_density_ref
	return gas_density_ref / bg


def compute_all_densities(
	oil_density_ref: float,
	water_density_ref: float,
	gas_density_ref: float,
	bo: float,
	bw: float,
	bg: float,
) -> dict[str, float]:
	"""Hitung densitas in-situ semua fasa sekaligus.

	Returns:
		Dict dengan key 'oil', 'water', 'gas' berisi densitas in-situ.
	"""
	return {
		"oil": compute_oil_density(oil_density_ref, bo),
		"water": compute_water_density(water_density_ref, bw),
		"gas": compute_gas_density(gas_density_ref, bg),
	}

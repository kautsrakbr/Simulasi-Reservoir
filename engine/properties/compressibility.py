from __future__ import annotations

"""Perhitungan kompresibilitas isothermal fluida reservoir.

Dua pendekatan tersedia:
1. Kompresibilitas konstan dari data referensi (slightly compressible fluid).
2. Kompresibilitas dari slope tabel PVT numerik (dB/dp per titik).

Konsisten dengan ReferenceData.oil_compressibility_reference dll. di domain/project.py.
"""


# ---------------------------------------------------------------------------
# 1. Kompresibilitas konstan (slightly compressible approximation)
# ---------------------------------------------------------------------------

def compute_oil_compressibility_const(oil_compressibility_ref: float) -> float:
	"""Kembalikan kompresibilitas oil konstan dari data referensi (1/psi).

	Model: B_o(p) ≈ B_o_ref * (1 + c_o * (p - p_ref))
		 => c_o ≈ -(1/B_o) * dB_o/dp = konstanta

	Args:
		oil_compressibility_ref: c_o dari ReferenceData (1/psi).

	Returns:
		Kompresibilitas oil (1/psi).
	"""
	return max(0.0, oil_compressibility_ref)


def compute_water_compressibility_const(water_compressibility_ref: float) -> float:
	"""Kembalikan kompresibilitas air konstan dari data referensi (1/psi)."""
	return max(0.0, water_compressibility_ref)


def compute_gas_compressibility_const(gas_compressibility_ref: float) -> float:
	"""Kembalikan kompresibilitas gas konstan dari data referensi (1/psi)."""
	return max(0.0, gas_compressibility_ref)


# ---------------------------------------------------------------------------
# 2. Kompresibilitas dari tabel PVT (slope numerik)
# ---------------------------------------------------------------------------

def _slope_from_table(table: list[tuple[float, float]], pressure: float) -> float:
	"""Hitung dB/dp di titik pressure menggunakan slope segmen terdekat."""
	if len(table) < 2:
		return 0.0
	for left, right in zip(table, table[1:]):
		p_l, b_l = left
		p_r, b_r = right
		if p_l <= pressure <= p_r:
			dp = p_r - p_l
			if abs(dp) < 1e-12:
				return 0.0
			return (b_r - b_l) / dp
	if pressure < table[0][0]:
		p_l, b_l = table[0]
		p_r, b_r = table[1]
		dp = p_r - p_l
		return (b_r - b_l) / dp if abs(dp) > 1e-12 else 0.0
	p_l, b_l = table[-2]
	p_r, b_r = table[-1]
	dp = p_r - p_l
	return (b_r - b_l) / dp if abs(dp) > 1e-12 else 0.0


def compute_oil_compressibility(
	pressure: float,
	bo_table: list[tuple[float, float]],
	current_bo: float,
) -> float:
	"""Hitung kompresibilitas oil dari slope tabel PVT: c_o = -(1/B_o) * dB_o/dp.

	Args:
		pressure: Tekanan cell saat ini (psi).
		bo_table: Tabel B_o vs pressure [(p, B_o), ...].
		current_bo: Nilai B_o saat ini (untuk normalisasi).

	Returns:
		Kompresibilitas oil efektif di tekanan tersebut (1/psi).
	"""
	if not bo_table or current_bo <= 0.0:
		return 0.0
	slope = _slope_from_table(bo_table, pressure)
	# c_o = -(1/Bo) * dBo/dp  (Bo biasanya bertambah dengan turunnya tekanan)
	return -slope / current_bo


def compute_water_compressibility(
	pressure: float,
	bw_table: list[tuple[float, float]],
	current_bw: float,
) -> float:
	"""Hitung kompresibilitas air dari slope tabel PVT."""
	if not bw_table or current_bw <= 0.0:
		return 0.0
	slope = _slope_from_table(bw_table, pressure)
	return -slope / current_bw


def compute_gas_compressibility(
	pressure: float,
	bg_table: list[tuple[float, float]],
	current_bg: float,
) -> float:
	"""Hitung kompresibilitas gas dari slope tabel PVT."""
	if not bg_table or current_bg <= 0.0:
		return 0.0
	slope = _slope_from_table(bg_table, pressure)
	return -slope / current_bg

from __future__ import annotations

"""Korelasi capillary pressure standalone (tanpa tabel interpolasi).

Dua model tersedia:
1. Brooks-Corey: model power-law standar untuk drainase dan imbibisi.
2. Linear: approksimasi sederhana untuk kasus tanpa data kapiler eksperimen.

Catatan: implementasi tabel-based (interpolasi dari SWOF/SGWOF) sudah ada
di relperm.py via kunci 'pcow' dan 'pcgw'. Modul ini menyediakan korelasi
analitik sebagai alternatif atau fallback.
"""

import math


# ---------------------------------------------------------------------------
# Model Brooks-Corey
# ---------------------------------------------------------------------------

def compute_pcow_brooks_corey(
	sw: float,
	swc: float,
	sor: float,
	pe: float,
	lambda_bc: float = 2.0,
) -> float:
	"""Capillary pressure oil-water model Brooks-Corey (psi).

	Formula (drainase):
		Se = (Sw - Swc) / (1 - Swc - Sor)
		Pcow = Pe * Se^(-1/lambda)

	Args:
		sw: Saturasi air saat ini (adimensional, 0–1).
		swc: Saturasi air connate / irreducible (adimensional).
		sor: Saturasi oil residual (adimensional).
		pe: Entry pressure (psi). Tekanan kapiler di Se = 1.
		lambda_bc: Pore size distribution index Brooks-Corey (adimensional).
		          Biasanya 1–5; makin besar makin seragam pore size.

	Returns:
		Capillary pressure Pcow (psi). Selalu >= 0.
	"""
	sw = max(swc, min(1.0 - sor, sw))
	se_denom = 1.0 - swc - sor
	if se_denom <= 0.0:
		return pe
	se = (sw - swc) / se_denom
	se = max(1e-6, min(1.0, se))
	if lambda_bc <= 0.0:
		return pe
	return pe * se ** (-1.0 / lambda_bc)


def compute_pcgw_brooks_corey(
	sg: float,
	sgc: float,
	swc: float,
	pe_gw: float,
	lambda_bc: float = 2.0,
) -> float:
	"""Capillary pressure gas-water model Brooks-Corey (psi).

	Args:
		sg: Saturasi gas saat ini.
		sgc: Saturasi gas kritis.
		swc: Saturasi air connate.
		pe_gw: Entry pressure gas-water (psi).
		lambda_bc: Pore size distribution index.

	Returns:
		Capillary pressure Pcgw (psi). Selalu >= 0.
	"""
	sg = max(sgc, min(1.0 - swc, sg))
	se_denom = 1.0 - swc - sgc
	if se_denom <= 0.0:
		return pe_gw
	se = (sg - sgc) / se_denom
	se = max(1e-6, min(1.0, se))
	if lambda_bc <= 0.0:
		return pe_gw
	return pe_gw * se ** (-1.0 / lambda_bc)


# ---------------------------------------------------------------------------
# Model Linear (fallback sederhana)
# ---------------------------------------------------------------------------

def compute_pcow(
	sw: float,
	swc: float = 0.2,
	pcow_max: float = 0.0,
) -> float:
	"""Capillary pressure oil-water model linear sederhana (psi).

	Formula:
		Pcow = Pcow_max * (1 - (Sw - Swc) / (1 - Swc))

	Menurun linear dari Pcow_max di Sw = Swc menjadi 0 di Sw = 1.
	Nilai default Pcow_max = 0 (no capillary pressure — konsisten dengan
	asumsi awal simulator sebelum data kapiler tersedia).

	Args:
		sw: Saturasi air saat ini.
		swc: Saturasi air irreducible.
		pcow_max: Capillary pressure maksimum di Sw = Swc (psi).

	Returns:
		Pcow (psi). Diclamp ke [0, Pcow_max].
	"""
	if pcow_max <= 0.0:
		return 0.0
	denom = 1.0 - swc
	if denom <= 0.0:
		return 0.0
	sw_norm = max(swc, min(1.0, sw))
	fraction = (sw_norm - swc) / denom
	return max(0.0, pcow_max * (1.0 - fraction))


def compute_pcgw(
	sg: float,
	sgc: float = 0.0,
	pcgw_max: float = 0.0,
) -> float:
	"""Capillary pressure gas-water model linear sederhana (psi).

	Menurun linear dari Pcgw_max di Sg = 1 - Swc menjadi 0 di Sg = Sgc.

	Args:
		sg: Saturasi gas saat ini.
		sgc: Saturasi gas kritis.
		pcgw_max: Capillary pressure maksimum (psi).

	Returns:
		Pcgw (psi). Diclamp ke [0, Pcgw_max].
	"""
	if pcgw_max <= 0.0:
		return 0.0
	denom = 1.0 - sgc
	if denom <= 0.0:
		return 0.0
	sg_norm = max(sgc, min(1.0, sg))
	fraction = (sg_norm - sgc) / denom
	return max(0.0, pcgw_max * fraction)

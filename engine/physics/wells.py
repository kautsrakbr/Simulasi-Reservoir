from __future__ import annotations

import math
from dataclasses import dataclass

from engine.domain.grid import GridModel
from engine.domain.state import ReservoirState
from engine.properties.pvt import interpolate_pvt
from engine.properties.relperm import interpolate_relperm


# Faktor konversi transmissibility standar (md·ft / (cp·psi·day))
_TRANS_UNIT = 0.00708


@dataclass(slots=True)
class WellDefinition:
	"""Definisi satu sumur dalam model reservoir.

	Attributes:
		name: Nama identifikasi sumur.
		cell_id: Indeks cell tempat sumur berlokasi (0-based flat index).
		well_radius: Jari-jari wellbore rw (ft).
		skin: Skin factor (adimensional). Positif = damage, negatif = stimulasi.
		bhp_target: Target bottom-hole pressure (psi). None jika pakai rate control.
		rate_target: Target laju produksi/injeksi permukaan (STB/day atau Mscf/day).
		             Positif = produksi, negatif = injeksi.
		phase: Fasa pengontrol rate ('oil', 'water', atau 'gas').
		is_producer: True = produsen, False = injector.
	"""
	name: str
	cell_id: int
	well_radius: float
	skin: float = 0.0
	bhp_target: float | None = None
	rate_target: float | None = None
	phase: str = "oil"
	is_producer: bool = True


def compute_peaceman_well_index(
	dx: float,
	dy: float,
	dz: float,
	perm_x: float,
	perm_y: float,
	well_radius: float,
	skin: float = 0.0,
) -> float:
	"""Hitung Peaceman well index (WI) untuk sumur vertikal di grid kartesian.

	Formula:
		r_e = 0.28 * sqrt(sqrt(ky/kx)*dx² + sqrt(kx/ky)*dy²)
		WI   = 0.00708 * sqrt(kx*ky) * dz / (ln(r_e/rw) + S)

	Satuan:
		dx, dy, dz [ft], perm_x, perm_y [md], well_radius [ft]
		WI kembali dalam [md·ft/cp] — konsisten dengan transmissibility unit simulator.

	Returns:
		Well index WI (md·ft/cp). 0.0 jika permeabilitas atau radius tidak valid.
	"""
	if perm_x <= 0.0 or perm_y <= 0.0 or well_radius <= 0.0 or dz <= 0.0:
		return 0.0

	k_geom = math.sqrt(perm_x * perm_y)
	ratio_yx = math.sqrt(perm_y / perm_x)
	ratio_xy = math.sqrt(perm_x / perm_y)
	r_equiv = 0.28 * math.sqrt(ratio_yx * dx * dx + ratio_xy * dy * dy)

	if r_equiv <= well_radius:
		r_equiv = max(well_radius * 1.5, r_equiv)

	denominator = math.log(r_equiv / well_radius) + skin
	if denominator <= 0.0:
		return 0.0

	return _TRANS_UNIT * k_geom * dz / denominator


def compute_well_phase_rate(
	well_index: float,
	kr: float,
	mu: float,
	b_factor: float,
	p_cell: float,
	p_bhp: float,
) -> float:
	"""Hitung laju alir fase tertentu dari satu sumur (STB/day atau Mscf/day permukaan).

	Formula:  q = WI * (kr / (mu * B)) * (p_cell - p_bhp)
	Positif = keluar dari reservoir (produksi), negatif = masuk (injeksi).

	Args:
		well_index: Peaceman WI (md·ft/cp).
		kr: Relative permeability fase (adimensional).
		mu: Viskositas fase (cp).
		b_factor: Formation volume factor fase (RB/STB atau RB/Mscf).
		p_cell: Tekanan cell (psi).
		p_bhp: Bottom-hole pressure target (psi).

	Returns:
		Laju alir permukaan (STB/day). Positif = produksi.
	"""
	if mu <= 0.0 or b_factor <= 0.0:
		return 0.0
	mobility = kr / mu
	return well_index * mobility * (p_cell - p_bhp) / b_factor


def _get_pvt(table_name: str, tables: dict[str, list[tuple[float, float]]], pressure: float, default: float) -> float:
	table = tables.get(table_name)
	if not table:
		return default
	return interpolate_pvt(table, pressure)


def _get_rock(table_name: str, tables: dict[str, list[tuple[float, float]]], saturation: float, default: float) -> float:
	table = tables.get(table_name)
	if not table:
		return default
	return interpolate_relperm(table, saturation)


def compute_well_source_terms(
	wells: list[WellDefinition],
	grid_model: GridModel,
	state: ReservoirState,
	pvt_tables: dict[str, list[tuple[float, float]]],
	rock_tables: dict[str, list[tuple[float, float]]],
) -> dict[str, list[float]]:
	"""Hitung suku sumber/sink sumur per cell untuk setiap fase.

	Returns:
		Dict berisi list per-cell untuk 'oil', 'water', 'gas'.
		Nilai positif = source (injeksi masuk reservoir).
		Nilai negatif = sink (produksi keluar reservoir).
	"""
	n = len(grid_model.cells)
	oil_q: list[float] = [0.0] * n
	water_q: list[float] = [0.0] * n
	gas_q: list[float] = [0.0] * n

	for well in wells:
		cell_id = well.cell_id
		if cell_id < 0 or cell_id >= n:
			continue
		if not grid_model.cells[cell_id].is_active:
			continue

		cell = grid_model.cells[cell_id]
		spec = grid_model.spec

		# Hitung Peaceman WI dari properti cell
		wi = compute_peaceman_well_index(
			dx=spec.dx,
			dy=spec.dy,
			dz=spec.dz,
			perm_x=cell.perm_x,
			perm_y=cell.perm_y,
			well_radius=well.well_radius,
			skin=well.skin,
		)
		if wi <= 0.0:
			continue

		pressure = state.pressure[cell_id]
		sw = max(0.0, min(1.0, state.sw[cell_id]))
		sg = max(0.0, min(1.0, state.sg[cell_id]))
		so = max(0.0, 1.0 - sw - sg)

		bo = _get_pvt("bo", pvt_tables, pressure, 1.0)
		bw = _get_pvt("bw", pvt_tables, pressure, 1.0)
		bg = _get_pvt("bg", pvt_tables, pressure, 1.0)
		mu_o = _get_pvt("mu_o", pvt_tables, pressure, 2.0)
		mu_w = _get_pvt("mu_w", pvt_tables, pressure, 1.0)
		mu_g = _get_pvt("mu_g", pvt_tables, pressure, 0.02)
		kro = _get_rock("kro", rock_tables, sw, max(0.0, so))
		krw = _get_rock("krw", rock_tables, sw, sw)
		krg = _get_rock("krg", rock_tables, sg, sg)

		# Tentukan BHP
		if well.bhp_target is not None:
			p_bhp = well.bhp_target
		else:
			# Jika rate control: hitung BHP balik dari target rate
			# Simplified: gunakan tekanan cell dikurangi estimasi pressure drop
			total_mob = (kro / mu_o if mu_o > 0 else 0.0) + \
						(krw / mu_w if mu_w > 0 else 0.0) + \
						(krg / mu_g if mu_g > 0 else 0.0)
			if well.rate_target is not None and wi > 0.0 and total_mob > 0.0:
				# q_total = WI * total_mob * (p_cell - p_bhp)
				p_bhp = pressure - well.rate_target / (wi * total_mob)
			else:
				p_bhp = pressure * 0.9  # fallback: 10% drawdown

		q_o = compute_well_phase_rate(wi, kro, mu_o, bo, pressure, p_bhp)
		q_w = compute_well_phase_rate(wi, krw, mu_w, bw, pressure, p_bhp)
		q_g = compute_well_phase_rate(wi, krg, mu_g, bg, pressure, p_bhp)

		# Tanda: negatif = sink (produksi keluar)
		sign = -1.0 if well.is_producer else 1.0
		oil_q[cell_id] += sign * q_o
		water_q[cell_id] += sign * q_w
		gas_q[cell_id] += sign * q_g

	return {"oil": oil_q, "water": water_q, "gas": gas_q}


def apply_well_terms(
	residual: list[float],
	well_sources: dict[str, list[float]],
	dt_days: float,
) -> list[float]:
	"""Tambahkan kontribusi suku sumur ke vektor residual.

	Well source term masuk ke residual sebagai:
		R_p[i] -= q_p[i] * dt   (source mengurangi residual karena membuat massa keluar)

	Args:
		residual: Vektor residual gabungan semua fasa (oil + water + gas, per cell).
		well_sources: Output dari compute_well_source_terms.
		dt_days: Ukuran time step (hari).

	Returns:
		Vektor residual baru yang sudah memperhitungkan well terms.
	"""
	result = list(residual)
	n = len(well_sources.get("oil", []))
	if n == 0 or dt_days <= 0.0:
		return result

	for phase_index, phase_key in enumerate(("oil", "water", "gas")):
		sources = well_sources.get(phase_key, [])
		for cell_id, q in enumerate(sources):
			residual_index = phase_index * n + cell_id
			if residual_index < len(result):
				result[residual_index] -= q * dt_days

	return result

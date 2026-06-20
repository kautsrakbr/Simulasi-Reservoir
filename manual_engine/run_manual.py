"""
manual_engine/run_manual.py
===========================
Simulasi reservoir 3-fase (oil/water/gas) fully-implicit — versi TERMINAL ONLY.
Tidak ada dependensi ke engine/, GUI, atau library eksternal apa pun.
Semua rumus ditulis inline agar mudah dibaca dan di-debug.

Jalankan:
    python manual_engine/run_manual.py
atau
    python -m manual_engine.run_manual

KONFIGURASI KASUS: edit bagian "=== KONFIGURASI ===" di bawah.
"""

from __future__ import annotations
import sys
import math

# Paksa UTF-8 agar karakter Unicode (─ ═ ✓ ✗ dll) tidak error di Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ══════════════════════════════════════════════════════════════════════════════
# KONSTANTA FISIK
# ══════════════════════════════════════════════════════════════════════════════

TRANSMISSIBILITY_UNIT_FACTOR = 0.00603   # md·ft²/(psi·day) → RB/day·psi
GRAVITY_GRAD = 0.433                      # psi/ft per sg=1

# ══════════════════════════════════════════════════════════════════════════════
# === KONFIGURASI — edit di sini ===
# ══════════════════════════════════════════════════════════════════════════════

# ── Grid ─────────────────────────────────────────────────────────────────────
NX, NY, NZ = 5, 5, 1          # jumlah sel (x, y, z)
DX, DY, DZ = 500.0, 500.0, 50.0   # ukuran sel (ft)

POROSITY       = 0.20          # porositas (fraksi)
PERM_X         = 100.0         # permeabilitas X (md)
PERM_Y         = 100.0         # permeabilitas Y (md)
PERM_Z         = 0.0           # permeabilitas Z (md, 0 = tidak ada aliran vertikal)
REFERENCE_DEPTH = 5000.0       # kedalaman referensi (ft)

# ── Kondisi Awal ─────────────────────────────────────────────────────────────
P_REF          = 3000.0        # tekanan referensi (psia)
INITIAL_SW     = 0.20          # saturasi air awal
INITIAL_SG     = 0.00          # saturasi gas awal

# ── Densitas Referensi (lbm/ft³) ─────────────────────────────────────────────
RHO_OIL_REF   = 50.0           # densitas oil (lbm/ft³)
RHO_WATER_REF = 62.4           # densitas air (lbm/ft³)
RHO_GAS_REF   = 0.9            # densitas gas (lbm/ft³)

# ── Kompresibilitas batuan ─────────────────────────────────────────────────────
ROCK_COMPRESS  = 3e-6          # 1/psi

# ── Tabel PVT: (pressure psia, nilai) ─────────────────────────────────────────
# Bo (RB/STB)
PVT_BO = [
    (500.0,  1.050),
    (1000.0, 1.080),
    (2000.0, 1.150),
    (3000.0, 1.200),
    (4000.0, 1.230),
    (5000.0, 1.250),
]
# Bw (RB/STB)
PVT_BW = [
    (500.0,  1.000),
    (1000.0, 1.001),
    (2000.0, 1.003),
    (3000.0, 1.005),
    (4000.0, 1.007),
    (5000.0, 1.009),
]
# Bg (RB/Mscf)
PVT_BG = [
    (500.0,  0.00500),
    (1000.0, 0.00260),
    (2000.0, 0.00140),
    (3000.0, 0.00095),
    (4000.0, 0.00073),
    (5000.0, 0.00060),
]
# mu_o (cp)
PVT_MU_O = [
    (500.0,  3.50),
    (1000.0, 2.80),
    (2000.0, 1.90),
    (3000.0, 1.40),
    (4000.0, 1.10),
    (5000.0, 0.90),
]
# mu_w (cp)
PVT_MU_W = [
    (500.0,  0.60),
    (1000.0, 0.60),
    (2000.0, 0.65),
    (3000.0, 0.70),
    (4000.0, 0.72),
    (5000.0, 0.74),
]
# mu_g (cp)
PVT_MU_G = [
    (500.0,  0.015),
    (1000.0, 0.018),
    (2000.0, 0.022),
    (3000.0, 0.026),
    (4000.0, 0.030),
    (5000.0, 0.034),
]

# ── Tabel Relperm: (saturasi, kr) ────────────────────────────────────────────
ROCK_KRO = [   # kro vs Sw
    (0.20, 1.000),
    (0.30, 0.800),
    (0.40, 0.550),
    (0.50, 0.330),
    (0.60, 0.160),
    (0.70, 0.050),
    (0.80, 0.000),
]
ROCK_KRW = [   # krw vs Sw
    (0.20, 0.000),
    (0.30, 0.020),
    (0.40, 0.060),
    (0.50, 0.120),
    (0.60, 0.210),
    (0.70, 0.340),
    (0.80, 1.000),
]
ROCK_KRG = [   # krg vs Sg
    (0.00, 0.000),
    (0.10, 0.020),
    (0.20, 0.070),
    (0.30, 0.170),
    (0.40, 0.320),
    (0.50, 0.540),
    (0.60, 1.000),
]
ROCK_PCOW = [  # Pc oil-water vs Sw (psi)
    (0.20, 5.0),
    (0.40, 2.0),
    (0.60, 0.5),
    (0.80, 0.0),
]
ROCK_PCGW = [  # Pc gas-water vs Sg (psi)
    (0.00, 0.0),
    (0.20, 2.0),
    (0.40, 6.0),
    (0.60, 12.0),
]

# ── Solver ───────────────────────────────────────────────────────────────────
DT_INITIAL      = 1.0     # timestep awal (hari)
DT_MIN          = 0.05    # timestep minimum (hari)
MAX_TIME        = 5.0     # waktu simulasi total (hari)
GROWTH_FACTOR   = 1.1     # faktor pertumbuhan dt
SHRINK_FACTOR   = 0.5     # faktor pengurangan dt saat gagal
MAX_RETRIES     = 5       # maks retry per step
MAX_NEWTON_ITER = 15      # maks iterasi Newton per step
RESID_TOL       = 0.05    # target residual norm ternormalisasi (|R|/skala)
PARAM_TOL       = 1e-4    # target perubahan parameter (dp/p, dSw, dSg)
PRESSURE_DAMP   = 0.7     # faktor damping tekanan
SAT_DAMP        = 0.7     # faktor damping saturasi
MAX_DP          = 200.0   # maks koreksi tekanan (psia)
MAX_DS          = 0.05    # maks koreksi saturasi

# ── Jacobian FD ──────────────────────────────────────────────────────────────
FD_DP  = 1.0    # perturbasi tekanan untuk finite difference (psi)
FD_DSW = 1e-4   # perturbasi Sw
FD_DSG = 1e-4   # perturbasi Sg

# ── Quasi-Newton (Broyden) ────────────────────────────────────────────────────
QUASI_NEWTON     = True  # aktifkan quasi-Newton; skip pada timestep 1
QN_REFRESH_EVERY = 5     # paksa reassemble penuh setiap N iterasi jika belum konvergen

# ── Output ───────────────────────────────────────────────────────────────────
VERBOSE_NEWTON = True   # tampilkan detail setiap iterasi Newton

# ══════════════════════════════════════════════════════════════════════════════
# HELPER — INTERPOLASI
# ══════════════════════════════════════════════════════════════════════════════

def interp(table: list[tuple[float, float]], x: float) -> float:
    """Interpolasi linear 1D; clamp di luar rentang."""
    if not table:
        return 1.0
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return table[-1][1]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def safe_div(num: float, den: float, fallback: float = 0.0) -> float:
    return num / den if abs(den) > 1e-14 else fallback

# ══════════════════════════════════════════════════════════════════════════════
# STRUKTUR DATA SEDERHANA (dict / list)
# ══════════════════════════════════════════════════════════════════════════════

# State  = {"p": [...], "sw": [...], "sg": [...]}
# Grid   = {"cells": [...], "connections": [...]}
# Cell   = {"id": int, "i","j","k": int, "depth": ft, "pv": ft³, "bulk_vol": ft³}
# Conn   = {"from": int, "to": int, "dir": str, "area": ft², "dist": ft, "T": md·ft}

# ══════════════════════════════════════════════════════════════════════════════
# BANGUN GRID
# ══════════════════════════════════════════════════════════════════════════════

def build_grid() -> dict:
    cells = []
    cid = 0
    bv = DX * DY * DZ
    for k in range(NZ):
        for j in range(NY):
            for i in range(NX):
                depth = REFERENCE_DEPTH + (k + 0.5) * DZ
                cells.append({
                    "id": cid, "i": i, "j": j, "k": k,
                    "depth": depth,
                    "bulk_vol": bv,
                    "poro": POROSITY,
                    "kx": PERM_X, "ky": PERM_Y, "kz": PERM_Z,
                })
                cid += 1

    connections = []
    plane = NX * NY
    for c in cells:
        ci = c["id"]
        i, j, k = c["i"], c["j"], c["k"]
        # Arah X+
        if i + 1 < NX:
            nid = ci + 1
            area = DY * DZ
            dist = DX
            T = _transmissibility(PERM_X, PERM_X, area, dist)
            connections.append({"from": ci, "to": nid, "dir": "x", "area": area, "dist": dist, "T": T})
        # Arah Y+
        if j + 1 < NY:
            nid = ci + NX
            area = DX * DZ
            dist = DY
            T = _transmissibility(PERM_Y, PERM_Y, area, dist)
            connections.append({"from": ci, "to": nid, "dir": "y", "area": area, "dist": dist, "T": T})
        # Arah Z+
        if k + 1 < NZ:
            nid = ci + plane
            area = DX * DY
            dist = DZ
            T = _transmissibility(PERM_Z, PERM_Z, area, dist)
            connections.append({"from": ci, "to": nid, "dir": "z", "area": area, "dist": dist, "T": T})

    return {"cells": cells, "connections": connections}


def _transmissibility(k1: float, k2: float, area: float, dist: float) -> float:
    """T = C_unit × (2k1k2/(k1+k2)) × A / d"""
    if k1 <= 0.0 or k2 <= 0.0 or dist <= 0.0:
        return 0.0
    k_harm = 2.0 * k1 * k2 / (k1 + k2)
    return TRANSMISSIBILITY_UNIT_FACTOR * k_harm * area / dist

# ══════════════════════════════════════════════════════════════════════════════
# INISIALISASI STATE
# ══════════════════════════════════════════════════════════════════════════════

def init_state(cells: list[dict]) -> dict:
    """
    Tekanan = hidrstatik dari referensi.
        P_i = P_ref + 0.433 × ρ_w × (depth_i − depth_ref)   [psia]
    Saturasi = seragam.
    """
    water_sg = RHO_WATER_REF / 62.4   # specific gravity (62.4 = air tawar lbm/ft³)
    gradient = GRAVITY_GRAD * water_sg  # psi/ft
    pressure = [P_REF + gradient * (c["depth"] - REFERENCE_DEPTH) for c in cells]
    sw = [INITIAL_SW] * len(cells)
    sg = [INITIAL_SG] * len(cells)
    return {"p": pressure, "sw": sw, "sg": sg}

# ══════════════════════════════════════════════════════════════════════════════
# PROPERTI SEL — PVT + RELPERM
# ══════════════════════════════════════════════════════════════════════════════

def cell_props(p: float, sw: float, sg: float) -> dict:
    """
    Kembalikan dict semua properti fasa di sel dengan tekanan p, saturasi sw/sg.
    so = 1 - sw - sg
    """
    sw  = clamp(sw, 0.0, 1.0)
    sg  = clamp(sg, 0.0, 1.0)
    so  = clamp(1.0 - sw - sg, 0.0, 1.0)

    bo   = interp(PVT_BO,   p)
    bw   = interp(PVT_BW,   p)
    bg   = interp(PVT_BG,   p)
    mu_o = interp(PVT_MU_O, p)
    mu_w = interp(PVT_MU_W, p)
    mu_g = interp(PVT_MU_G, p)

    kro  = interp(ROCK_KRO,  sw)   # kro vs Sw
    krw  = interp(ROCK_KRW,  sw)   # krw vs Sw
    krg  = interp(ROCK_KRG,  sg)   # krg vs Sg
    pcow = interp(ROCK_PCOW, sw)   # Pc oil-water vs Sw
    pcgw = interp(ROCK_PCGW, sg)   # Pc gas-water vs Sg

    # Densitas di kondisi reservoir (lbm/ft³)
    rho_o = safe_div(RHO_OIL_REF,   bo,  RHO_OIL_REF)
    rho_w = safe_div(RHO_WATER_REF, bw,  RHO_WATER_REF)
    rho_g = safe_div(RHO_GAS_REF,   bg,  RHO_GAS_REF)

    # Mobilitas λ = kr/μ (1/cp)
    lam_o = safe_div(kro, mu_o, 0.0)
    lam_w = safe_div(krw, mu_w, 0.0)
    lam_g = safe_div(krg, mu_g, 0.0)

    return {
        "bo": bo, "bw": bw, "bg": bg,
        "mu_o": mu_o, "mu_w": mu_w, "mu_g": mu_g,
        "kro": kro, "krw": krw, "krg": krg,
        "pcow": pcow, "pcgw": pcgw,
        "rho_o": rho_o, "rho_w": rho_w, "rho_g": rho_g,
        "lam_o": lam_o, "lam_w": lam_w, "lam_g": lam_g,
        "so": so, "sw": sw, "sg": sg,
    }

# ══════════════════════════════════════════════════════════════════════════════
# PORE VOLUME EFEKTIF
# ══════════════════════════════════════════════════════════════════════════════

def pore_volume(cell: dict, p: float) -> float:
    """
    PV = Vb × φ × [1 + cf × (p − p_ref)]
    """
    scale = 1.0 + ROCK_COMPRESS * (p - P_REF)
    scale = max(scale, 0.0)
    return cell["bulk_vol"] * cell["poro"] * scale

# ══════════════════════════════════════════════════════════════════════════════
# POTENSI ALIRAN (DARCY)
# ══════════════════════════════════════════════════════════════════════════════

def potential_oil(p_from: float, p_to: float, rho_from: float, rho_to: float, ddepth: float) -> float:
    """
    Φ_o = (p_to − p_from) − ρ_avg × Δz / 144
    Δz = depth_to − depth_from  (ft, positif ke bawah)
    ρ dalam lbm/ft³, /144 untuk konversi ke psi
    """
    rho_avg = 0.5 * (rho_from + rho_to)
    grav = rho_avg * ddepth / 144.0
    return (p_to - p_from) - grav


def potential_water(p_from, p_to, rho_from, rho_to, ddepth, pcow_from, pcow_to):
    """Φ_w = Φ_o + (Pcow_to − Pcow_from)"""
    rho_avg = 0.5 * (rho_from + rho_to)
    grav = rho_avg * ddepth / 144.0
    cap  = pcow_to - pcow_from
    return (p_to - p_from) - grav - cap


def potential_gas(p_from, p_to, rho_from, rho_to, ddepth, pcgw_from, pcgw_to):
    """Φ_g = Φ_o + (Pcgw_to − Pcgw_from)"""
    rho_avg = 0.5 * (rho_from + rho_to)
    grav = rho_avg * ddepth / 144.0
    cap  = pcgw_to - pcgw_from
    return (p_to - p_from) - grav + cap

# ══════════════════════════════════════════════════════════════════════════════
# FLUX ANTAR SEL (DARCY MULTIFASA)
# ══════════════════════════════════════════════════════════════════════════════

def compute_connection_flux(
    conn: dict,
    props_from: dict, props_to: dict,
    p_from: float, p_to: float,
    depth_from: float, depth_to: float,
) -> dict:
    """
    q_α = −T × λ_α_upstream × Φ_α / B_α_avg    [RB/day]
    Upwinding: upstream = sel dengan Φ_α lebih rendah (aliran mengalir dari tinggi ke rendah).
    Konvensi: positif = keluar dari sel from_cell.
    """
    T = conn["T"]
    ddepth = depth_to - depth_from

    # ── Oil ──
    phi_o = potential_oil(p_from, p_to, props_from["rho_o"], props_to["rho_o"], ddepth)
    up_o  = props_from if phi_o <= 0.0 else props_to
    b_avg_o = 0.5 * (props_from["bo"] + props_to["bo"])
    q_o = -T * up_o["lam_o"] * phi_o / max(b_avg_o, 1e-14)

    # ── Water ──
    phi_w = potential_water(p_from, p_to, props_from["rho_w"], props_to["rho_w"], ddepth,
                            props_from["pcow"], props_to["pcow"])
    up_w  = props_from if phi_w <= 0.0 else props_to
    b_avg_w = 0.5 * (props_from["bw"] + props_to["bw"])
    q_w = -T * up_w["lam_w"] * phi_w / max(b_avg_w, 1e-14)

    # ── Gas ──
    phi_g = potential_gas(p_from, p_to, props_from["rho_g"], props_to["rho_g"], ddepth,
                          props_from["pcgw"], props_to["pcgw"])
    up_g  = props_from if phi_g <= 0.0 else props_to
    b_avg_g = 0.5 * (props_from["bg"] + props_to["bg"])
    q_g = -T * up_g["lam_g"] * phi_g / max(b_avg_g, 1e-14)

    return {"oil": q_o, "water": q_w, "gas": q_g,
            "phi_o": phi_o, "phi_w": phi_w, "phi_g": phi_g}


def compute_net_flux(grid: dict, state: dict) -> dict:
    """
    Net flux per sel = Σ_koneksi flux (dengan tanda).
    Positif = netto masuk ke sel (inflow).
    """
    n = len(grid["cells"])
    net_o = [0.0] * n
    net_w = [0.0] * n
    net_g = [0.0] * n
    conn_fluxes = []

    for conn in grid["connections"]:
        fi  = conn["from"]
        ti  = conn["to"]
        p_f = state["p"][fi]
        p_t = state["p"][ti]
        d_f = grid["cells"][fi]["depth"]
        d_t = grid["cells"][ti]["depth"]
        pr_f = cell_props(p_f, state["sw"][fi], state["sg"][fi])
        pr_t = cell_props(p_t, state["sw"][ti], state["sg"][ti])
        flux = compute_connection_flux(conn, pr_f, pr_t, p_f, p_t, d_f, d_t)
        conn_fluxes.append(flux)
        # flux positif = keluar dari fi → masuk ke ti
        net_o[fi] -= flux["oil"];  net_o[ti] += flux["oil"]
        net_w[fi] -= flux["water"]; net_w[ti] += flux["water"]
        net_g[fi] -= flux["gas"];  net_g[ti] += flux["gas"]

    return {
        "oil": net_o, "water": net_w, "gas": net_g,
        "conn": conn_fluxes,
    }

# ══════════════════════════════════════════════════════════════════════════════
# AKUMULASI (PERUBAHAN MASSA / WAKTU)
# ══════════════════════════════════════════════════════════════════════════════

def compute_accumulation(grid: dict, state_n: dict, state_k: dict, dt: float) -> dict:
    """
    Acc_oil_i   = (PV_k × So_k / Bo_k  −  PV_n × So_n / Bo_n) / dt
    Acc_water_i = (PV_k × Sw_k / Bw_k  −  PV_n × Sw_n / Bw_n) / dt
    Acc_gas_i   = (PV_k × Sg_k / Bg_k  −  PV_n × Sg_n / Bg_n) / dt
    """
    dt = max(dt, 1e-14)
    acc_o, acc_w, acc_g, acc_tot = [], [], [], []
    for i, cell in enumerate(grid["cells"]):
        pn = state_n["p"][i];  pk = state_k["p"][i]
        sw_n = clamp(state_n["sw"][i], 0.0, 1.0)
        sg_n = clamp(state_n["sg"][i], 0.0, 1.0)
        sw_k = clamp(state_k["sw"][i], 0.0, 1.0)
        sg_k = clamp(state_k["sg"][i], 0.0, 1.0)
        so_n = clamp(1.0 - sw_n - sg_n, 0.0, 1.0)
        so_k = clamp(1.0 - sw_k - sg_k, 0.0, 1.0)

        pv_n = pore_volume(cell, pn)
        pv_k = pore_volume(cell, pk)

        bo_n = interp(PVT_BO, pn); bo_k = interp(PVT_BO, pk)
        bw_n = interp(PVT_BW, pn); bw_k = interp(PVT_BW, pk)
        bg_n = interp(PVT_BG, pn); bg_k = interp(PVT_BG, pk)

        ao = (safe_div(pv_k * so_k, bo_k, 0.0) - safe_div(pv_n * so_n, bo_n, 0.0)) / dt
        aw = (safe_div(pv_k * sw_k, bw_k, 0.0) - safe_div(pv_n * sw_n, bw_n, 0.0)) / dt
        ag = (safe_div(pv_k * sg_k, bg_k, 0.0) - safe_div(pv_n * sg_n, bg_n, 0.0)) / dt

        acc_o.append(ao)
        acc_w.append(aw)
        acc_g.append(ag)
        acc_tot.append(ao + aw + ag)

    return {"oil": acc_o, "water": acc_w, "gas": acc_g, "total": acc_tot}

# ══════════════════════════════════════════════════════════════════════════════
# RESIDUAL
# ══════════════════════════════════════════════════════════════════════════════

def compute_residual(net_flux: dict, acc: dict) -> dict:
    """
    R_α_i = NetFlux_α_i − Acc_α_i     (persamaan konservasi massa)
    Konvergen bila |R| → 0.
    """
    n = len(acc["oil"])
    r_o = [net_flux["oil"][i] - acc["oil"][i]   for i in range(n)]
    r_w = [net_flux["water"][i] - acc["water"][i] for i in range(n)]
    r_g = [net_flux["gas"][i] - acc["gas"][i]   for i in range(n)]
    r_tot = [net_flux["oil"][i] + net_flux["water"][i] + net_flux["gas"][i]
             - acc["total"][i] for i in range(n)]
    # Vektor residual gabungan: [R_oil_1..n | R_water_1..n | R_gas_1..n]
    r_vec = r_o + r_w + r_g
    return {"oil": r_o, "water": r_w, "gas": r_g, "total": r_tot, "vec": r_vec}


def residual_norm(resid: dict, net_flux: dict, acc: dict) -> float:
    """
    Norm ternormalisasi = max|R_vec| / max(max|Q|, max|Acc|, 1)
    """
    max_r = max((abs(v) for v in resid["vec"]), default=0.0)
    max_q = max(
        (abs(v) for vlist in (net_flux["oil"], net_flux["water"], net_flux["gas"]) for v in vlist),
        default=0.0,
    )
    max_a = max(
        (abs(v) for vlist in (acc["oil"], acc["water"], acc["gas"]) for v in vlist),
        default=0.0,
    )
    scale = max(max_q, max_a, 1.0)
    return max_r / scale

# ══════════════════════════════════════════════════════════════════════════════
# JACOBIAN — FINITE DIFFERENCE
# ══════════════════════════════════════════════════════════════════════════════

def _state_copy(s: dict) -> dict:
    return {"p": list(s["p"]), "sw": list(s["sw"]), "sg": list(s["sg"])}


def _eval_residual_vec(grid: dict, state_n: dict, state_k: dict, dt: float) -> list[float]:
    nf  = compute_net_flux(grid, state_k)
    acc = compute_accumulation(grid, state_n, state_k, dt)
    return compute_residual(nf, acc)["vec"]


def assemble_jacobian(grid: dict, state_n: dict, state_k: dict, dt: float) -> list[list[float]]:
    """
    J ≈ ∂R/∂x  via forward finite-difference.
    x = [p_1..n, Sw_1..n, Sg_1..n]  → dimensi 3n × 3n
    J_ij = (R_i(x + ε e_j) − R_i(x)) / ε
    """
    n  = len(grid["cells"])
    r0 = _eval_residual_vec(grid, state_n, state_k, dt)
    m  = len(r0)       # = 3n
    J  = [[0.0] * m for _ in range(m)]

    # Perturb tekanan
    for j in range(n):
        s2 = _state_copy(state_k)
        eps = max(FD_DP, abs(s2["p"][j]) * 1e-6)
        s2["p"][j] += eps
        r1 = _eval_residual_vec(grid, state_n, s2, dt)
        for i in range(m):
            J[i][j] = (r1[i] - r0[i]) / eps

    # Perturb Sw
    for j in range(n):
        s2 = _state_copy(state_k)
        eps = FD_DSW
        s2["sw"][j] = clamp(s2["sw"][j] + eps, 0.0, 1.0)
        r1 = _eval_residual_vec(grid, state_n, s2, dt)
        for i in range(m):
            J[i][n + j] = (r1[i] - r0[i]) / eps

    # Perturb Sg
    for j in range(n):
        s2 = _state_copy(state_k)
        eps = FD_DSG
        s2["sg"][j] = clamp(s2["sg"][j] + eps, 0.0, 1.0)
        r1 = _eval_residual_vec(grid, state_n, s2, dt)
        for i in range(m):
            J[i][2 * n + j] = (r1[i] - r0[i]) / eps

    return J

# ══════════════════════════════════════════════════════════════════════════════
# SOLVER LINEAR — GAUSSIAN ELIMINATION (PARTIAL PIVOTING)
# ══════════════════════════════════════════════════════════════════════════════

def gauss_solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Selesaikan Ax = b dengan eliminasi Gauss + partial pivoting."""
    n = len(b)
    # Augmented matrix
    M = [list(A[i]) + [b[i]] for i in range(n)]
    EPS = 1e-14

    for col in range(n):
        # Cari pivot terbesar di kolom ini
        max_val = abs(M[col][col])
        max_row = col
        for row in range(col + 1, n):
            if abs(M[row][col]) > max_val:
                max_val = abs(M[row][col])
                max_row = row
        if max_val < EPS:
            raise ValueError(f"Matrix singular pada kolom {col} (pivot < {EPS:.1e}).")
        M[col], M[max_row] = M[max_row], M[col]

        piv = M[col][col]
        for row in range(col + 1, n):
            f = M[row][col] / piv
            if abs(f) < EPS:
                continue
            for k in range(col, n + 1):
                M[row][k] -= f * M[col][k]

    # Back substitution
    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        s = M[row][n]
        for k in range(row + 1, n):
            s -= M[row][k] * x[k]
        piv = M[row][row]
        if abs(piv) < EPS:
            raise ValueError(f"Pivot nol pada back-substitution baris {row}.")
        x[row] = s / piv
    return x

# ══════════════════════════════════════════════════════════════════════════════
# QUASI-NEWTON — BROYDEN RANK-1 UPDATE
# ══════════════════════════════════════════════════════════════════════════════

def broyden_update(
    J: list[list[float]],
    s: list[float],
    y: list[float],
) -> list[list[float]]:
    """
    Broyden rank-1 update:  J_new = J + (y − J·s) s^T / (s^T s)
    s = x_new − x_old  (perubahan state aktual setelah damping)
    y = R_new − R_old  (perubahan residual)
    Jika ‖s‖ terlalu kecil, kembalikan J asli tanpa update.
    """
    ss = sum(si * si for si in s)
    if ss < 1e-28:
        return J
    m = len(s)
    Js = [sum(J[i][k] * s[k] for k in range(m)) for i in range(m)]
    J_new = [list(row) for row in J]
    for i in range(m):
        c = (y[i] - Js[i]) / ss
        for j in range(m):
            J_new[i][j] += c * s[j]
    return J_new


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE STATE — NEWTON STEP
# ══════════════════════════════════════════════════════════════════════════════

def apply_correction(state_k: dict, delta: list[float]) -> dict:
    """
    x_new = x_old + α × Δx
    Δx = −J⁻¹ R  (delta sudah di-solve dari sistem Ax = -R)
    Dengan damping dan clamping.
    """
    n = len(state_k["p"])
    p_new  = list(state_k["p"])
    sw_new = list(state_k["sw"])
    sg_new = list(state_k["sg"])

    for i in range(n):
        dp = clamp(delta[i],         -MAX_DP, MAX_DP)
        p_new[i] = max(14.7, state_k["p"][i] + PRESSURE_DAMP * dp)

    for i in range(n):
        dsw = clamp(delta[n + i],     -MAX_DS, MAX_DS)
        dsg = clamp(delta[2 * n + i], -MAX_DS, MAX_DS)
        sw_i = clamp(state_k["sw"][i] + SAT_DAMP * dsw, 0.0, 1.0)
        sg_i = clamp(state_k["sg"][i] + SAT_DAMP * dsg, 0.0, 1.0)
        if sw_i + sg_i > 1.0:
            tot = sw_i + sg_i
            sw_i /= tot; sg_i /= tot
        sw_new[i] = sw_i
        sg_new[i] = sg_i

    return {"p": p_new, "sw": sw_new, "sg": sg_new}

# ══════════════════════════════════════════════════════════════════════════════
# PRINT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

SEP  = "-" * 72
SEP2 = "=" * 72

def _hdr(text: str) -> None:
    print(f"\n{SEP2}\n  {text}\n{SEP2}")

def _sub(text: str) -> None:
    print(f"\n{SEP}\n  {text}\n{SEP}")


def print_grid_info(grid: dict) -> None:
    _hdr(f"GRID  {NX}×{NY}×{NZ}  ({len(grid['cells'])} sel, {len(grid['connections'])} koneksi)")
    print(f"  DX={DX} ft  DY={DY} ft  DZ={DZ} ft")
    print(f"  Porositas={POROSITY}  Kx={PERM_X} md  Ky={PERM_Y} md  Kz={PERM_Z} md")
    print(f"  Unit faktor transmisibilitas = {TRANSMISSIBILITY_UNIT_FACTOR}")
    print()
    print(f"  {'Koneksi':>4}  {'From':>5}  {'To':>5}  {'Arah':>4}  {'Area (ft²)':>12}  "
          f"{'Dist (ft)':>10}  {'T (md·ft)':>12}")
    for ci, c in enumerate(grid["connections"]):
        print(f"  {ci+1:>4}  {c['from']:>5}  {c['to']:>5}  {c['dir']:>4}  "
              f"{c['area']:>12.1f}  {c['dist']:>10.1f}  {c['T']:>12.5f}")


def print_state(state: dict, label: str = "State") -> None:
    _sub(label)
    n = len(state["p"])
    print(f"  {'Sel':>4}  {'P (psia)':>12}  {'Sw':>8}  {'Sg':>8}  {'So':>8}")
    for i in range(n):
        so = clamp(1.0 - state["sw"][i] - state["sg"][i], 0.0, 1.0)
        print(f"  {i+1:>4}  {state['p'][i]:>12.3f}  {state['sw'][i]:>8.4f}  "
              f"{state['sg'][i]:>8.4f}  {so:>8.4f}")


def print_flux(net_flux: dict) -> None:
    print()
    print(f"  {'Sel':>4}  {'NetFlux Oil':>14}  {'NetFlux Water':>14}  {'NetFlux Gas':>14}")
    n = len(net_flux["oil"])
    for i in range(n):
        print(f"  {i+1:>4}  {net_flux['oil'][i]:>14.5e}  "
              f"{net_flux['water'][i]:>14.5e}  {net_flux['gas'][i]:>14.5e}")


def print_accumulation(acc: dict) -> None:
    print()
    print(f"  {'Sel':>4}  {'Acc Oil':>14}  {'Acc Water':>14}  {'Acc Gas':>14}")
    n = len(acc["oil"])
    for i in range(n):
        print(f"  {i+1:>4}  {acc['oil'][i]:>14.5e}  "
              f"{acc['water'][i]:>14.5e}  {acc['gas'][i]:>14.5e}")


def print_residual(resid: dict, norm: float) -> None:
    print()
    print(f"  {'Sel':>4}  {'R_oil':>14}  {'R_water':>14}  {'R_gas':>14}")
    n = len(resid["oil"])
    for i in range(n):
        print(f"  {i+1:>4}  {resid['oil'][i]:>14.5e}  "
              f"{resid['water'][i]:>14.5e}  {resid['gas'][i]:>14.5e}")
    print(f"\n  max|R_oil|  = {max(abs(v) for v in resid['oil']):.5e}")
    print(f"  max|R_water|= {max(abs(v) for v in resid['water']):.5e}")
    print(f"  max|R_gas|  = {max(abs(v) for v in resid['gas']):.5e}")
    print(f"  Norm (ternorm) = {norm:.5e}   target < {RESID_TOL}")

# ══════════════════════════════════════════════════════════════════════════════
# TIMESTEP — NEWTON LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run_timestep(
    grid: dict,
    state_n: dict,
    dt: float,
    t_end: float,
    step_no: int,
    J_prev: list[list[float]] | None = None,
) -> tuple[dict, bool, float, int, list[list[float]] | None]:
    """
    Jalankan satu timestep dengan Newton (atau quasi-Newton Broyden) iteration.

    J_prev : Jacobian konvergen dari timestep sebelumnya.
             None  → selalu assembe J penuh (full Newton).
             nilai → dipakai sebagai J awal, di-update Broyden tiap iterasi,
                     di-refresh setiap QN_REFRESH_EVERY iterasi.

    Kembalikan (state_baru, konvergen, norm_akhir, jumlah_iterasi, J_final).
    """
    state_k = _state_copy(state_n)
    state_k["p"] = [max(14.7, p - 2.0) for p in state_k["p"]]

    prev_state_for_delta: dict | None = None
    converged = False
    norm_final = 1e30
    used_iter  = 0

    # Jacobian saat ini; akan diisi saat iterasi pertama
    J_current: list[list[float]] | None = J_prev

    # Untuk Broyden: simpan residual & perubahan state dari iterasi sebelumnya
    r_prev:   list[float] | None = None
    x_prev:   list[float] | None = None   # [p_1..n | sw_1..n | sg_1..n]

    use_quasi = QUASI_NEWTON and (J_prev is not None)

    if VERBOSE_NEWTON:
        mode = "Quasi-Newton (Broyden)" if use_quasi else "Full Newton"
        print(f"\n  -- Newton Loop  (dt={dt:.4f} d, t_end={t_end:.4f} d)  [{mode}] --")

    for it in range(1, MAX_NEWTON_ITER + 1):
        used_iter = it
        nf    = compute_net_flux(grid, state_k)
        acc   = compute_accumulation(grid, state_n, state_k, dt)
        resid = compute_residual(nf, acc)
        norm  = residual_norm(resid, nf, acc)
        norm_final = norm

        # ── Konvergensi ───────────────────────────────────────────────────
        crit1 = norm <= RESID_TOL

        if prev_state_for_delta is not None:
            n_cells = len(state_k["p"])
            max_dp_rel = max(
                abs(state_k["p"][i] - prev_state_for_delta["p"][i])
                / max(abs(prev_state_for_delta["p"][i]), 1.0)
                for i in range(n_cells)
            )
            max_dsw = max(abs(state_k["sw"][i] - prev_state_for_delta["sw"][i]) for i in range(n_cells))
            max_dsg = max(abs(state_k["sg"][i] - prev_state_for_delta["sg"][i]) for i in range(n_cells))
            crit2 = max(max_dp_rel, max_dsw, max_dsg) <= PARAM_TOL
        else:
            crit2 = False

        if VERBOSE_NEWTON:
            if crit1 and crit2:
                tag = "  <- KONVERGEN"
            elif crit1:
                tag = "  (norm OK, param belum)"
            elif crit2:
                tag = "  (param OK, norm belum)"
            else:
                tag = ""
            print(f"    Iter {it:>2}: norm={norm:.4e}  crit1={crit1}  crit2={crit2}{tag}")

        if crit1 and crit2:
            converged = True
            if VERBOSE_NEWTON:
                print(f"    -> Konvergen dalam {it} iterasi Newton")
            break

        prev_state_for_delta = _state_copy(state_k)

        # ── Bangun / update Jacobian ──────────────────────────────────────
        need_full = (
            J_current is None                         # belum ada J sama sekali
            or not use_quasi                          # mode full Newton
            or (it % QN_REFRESH_EVERY == 1 and it > 1)  # refresh berkala
        )

        if need_full:
            J_current = assemble_jacobian(grid, state_n, state_k, dt)
            if VERBOSE_NEWTON and use_quasi:
                print(f"      [J: assembe penuh iter {it}]")
        elif r_prev is not None and x_prev is not None:
            # Broyden rank-1 update
            n_cells = len(state_k["p"])
            x_cur = state_k["p"] + state_k["sw"] + state_k["sg"]
            s = [x_cur[i] - x_prev[i] for i in range(len(x_cur))]
            y = [resid["vec"][i] - r_prev[i] for i in range(len(r_prev))]
            J_current = broyden_update(J_current, s, y)
            if VERBOSE_NEWTON:
                print(f"      [J: Broyden update iter {it}]")

        # Simpan residual & state untuk Broyden iterasi berikutnya
        r_prev = list(resid["vec"])
        x_prev = state_k["p"] + state_k["sw"] + state_k["sg"]

        # ── Selesaikan sistem linear dan update state ─────────────────────
        try:
            r_neg   = [-v for v in resid["vec"]]
            delta   = gauss_solve(J_current, r_neg)
            state_k = apply_correction(state_k, delta)
        except ValueError as e:
            if VERBOSE_NEWTON:
                print(f"    [!] Solver gagal ({e}), relaksasi tekanan.")
            p_new = [max(14.7, state_k["p"][i] - 0.02 * resid["total"][i])
                     for i in range(len(state_k["p"]))]
            state_k   = {"p": p_new, "sw": list(state_k["sw"]), "sg": list(state_k["sg"])}
            J_current = None   # paksa reassemble di iterasi berikutnya

    return state_k, converged, norm_final, used_iter, J_current

# ══════════════════════════════════════════════════════════════════════════════
# LOOP SIMULASI UTAMA
# ══════════════════════════════════════════════════════════════════════════════

def run_simulation(grid: dict) -> None:
    _hdr("SIMULASI RESERVOIR — FULLY IMPLICIT 3-FASE")
    print(f"  Kasus : {NX}×{NY}×{NZ} grid  ({len(grid['cells'])} sel)")
    print(f"  Waktu : 0 → {MAX_TIME} hari")
    print(f"  dt awal={DT_INITIAL} d  dtMin={DT_MIN} d  Newton={MAX_NEWTON_ITER} iter  "
          f"Tol_norm={RESID_TOL}  Tol_param={PARAM_TOL}")
    print_grid_info(grid)

    state = init_state(grid["cells"])
    print_state(state, "STATE AWAL")

    t        = 0.0
    dt       = DT_INITIAL
    step_no  = 0
    step_log: list[dict] = []
    J_carried: list[list[float]] | None = None   # Jacobian dibawa antar timestep

    while t < MAX_TIME - 1e-12:
        remaining = MAX_TIME - t
        trial_dt  = min(dt, remaining)
        t_end     = t + trial_dt
        step_no  += 1

        _hdr(f"TIMESTEP {step_no}  →  t = {t:.4f} + {trial_dt:.4f} = {t_end:.4f} hari")

        # Timestep 1 selalu full Newton; quasi-Newton mulai timestep 2
        J_init = J_carried if (QUASI_NEWTON and step_no > 1) else None

        accepted    = False
        retry       = 0
        final_state = state
        final_norm  = 1e30
        final_iter  = 0
        final_J     = J_init

        for retry in range(MAX_RETRIES + 1):
            if retry > 0:
                print(f"\n  ↺ Retry {retry}: dt = {trial_dt:.4f} → ", end="")
                trial_dt = max(trial_dt * SHRINK_FACTOR, DT_MIN)
                t_end    = t + trial_dt
                print(f"{trial_dt:.4f} hari")
                if trial_dt < DT_MIN:
                    print("  [!] dt minimum tercapai, hentikan simulasi.")
                    break

            new_state, conv, norm, n_iter, J_out = run_timestep(
                grid, state, trial_dt, t_end, step_no, J_prev=J_init
            )

            final_state = new_state
            final_norm  = norm
            final_iter  = n_iter
            final_J     = J_out

            if conv:
                accepted = True
                break
            else:
                print(f"  ✗ Tidak konvergen (norm={norm:.4e}), retry...")
                J_init = None   # reset J saat retry agar full Newton

        # ── Tampilkan state setelah step ──────────────────────────────────
        conv_str = "✓ konvergen" if accepted else "✗ GAGAL"
        print(f"\n  Hasil: {conv_str}  |  {final_iter} iterasi Newton  |  "
              f"norm={final_norm:.4e}  |  retry={retry}")

        if VERBOSE_NEWTON:
            print_state(final_state, f"State t = {t_end:.4f} hari")

        # ── Simpan log ────────────────────────────────────────────────────
        step_log.append({
            "step": step_no, "t": t_end, "dt": trial_dt,
            "conv": accepted, "iter": final_iter, "norm": final_norm,
            "p_avg": sum(final_state["p"]) / len(final_state["p"]),
            "sw_avg": sum(final_state["sw"]) / len(final_state["sw"]),
            "sg_avg": sum(final_state["sg"]) / len(final_state["sg"]),
        })

        if not accepted:
            print("\n  [!] Simulasi dihentikan karena tidak konvergen.")
            break

        # ── Accept ───────────────────────────────────────────────────────
        state     = final_state
        J_carried = final_J    # bawa Jacobian ke timestep berikutnya
        t         = t_end
        dt        = trial_dt * GROWTH_FACTOR

    # ══════════════════════════════════════════════════════════════════════
    # RINGKASAN AKHIR
    # ══════════════════════════════════════════════════════════════════════
    _hdr("RINGKASAN SIMULASI")
    n_ok = sum(1 for s in step_log if s["conv"])
    print(f"  Total step    : {len(step_log)}")
    print(f"  Konvergen     : {n_ok}")
    print(f"  Gagal         : {len(step_log) - n_ok}")
    print(f"  Waktu akhir   : {step_log[-1]['t']:.4f} hari" if step_log else "  (tidak ada step)")
    print()
    print(f"  {'Step':>5}  {'t (hari)':>10}  {'dt (hari)':>10}  "
          f"{'Iter':>5}  {'Norm':>12}  {'P_avg (psia)':>14}  "
          f"{'Sw_avg':>8}  {'Sg_avg':>8}  {'Status':>12}")
    print("  " + "─" * 90)
    for s in step_log:
        ok = "✓ konvergen" if s["conv"] else "✗ gagal"
        print(f"  {s['step']:>5}  {s['t']:>10.4f}  {s['dt']:>10.4f}  "
              f"{s['iter']:>5}  {s['norm']:>12.4e}  {s['p_avg']:>14.3f}  "
              f"{s['sw_avg']:>8.4f}  {s['sg_avg']:>8.4f}  {ok:>12}")

    print()
    _hdr("STATE AKHIR")
    print_state(state, "")

    # ── Diagnostik satu step terakhir ─────────────────────────────────────
    _hdr("DIAGNOSTIK LENGKAP — STEP TERAKHIR")
    nf   = compute_net_flux(grid, state)
    acc  = compute_accumulation(grid, step_log[-1] and state or state, state, step_log[-1]["dt"] if step_log else 1.0)
    resid = compute_residual(nf, acc)
    norm  = residual_norm(resid, nf, acc)

    _sub("Net Flux per Sel (RB/day)")
    print_flux(nf)
    _sub("Akumulasi per Sel (RB/day)")
    print_accumulation(acc)
    _sub("Residual per Sel")
    print_residual(resid, norm)

    _sub("Detail Koneksi (step terakhir)")
    print(f"  {'Conn':>5}  {'From':>5}  {'To':>5}  "
          f"{'q_oil':>12}  {'q_water':>12}  {'q_gas':>12}  "
          f"{'Φ_oil':>10}  {'Φ_water':>10}  {'Φ_gas':>10}")
    for ci, (conn, flux) in enumerate(zip(grid["connections"], nf.get("conn", []))):
        cf = flux if isinstance(flux, dict) else {}
        print(f"  {ci+1:>5}  {conn['from']+1:>5}  {conn['to']+1:>5}  "
              f"{cf.get('oil', 0):>12.4e}  {cf.get('water', 0):>12.4e}  "
              f"{cf.get('gas', 0):>12.4e}  "
              f"{cf.get('phi_o', 0):>10.4f}  {cf.get('phi_w', 0):>10.4f}  "
              f"{cf.get('phi_g', 0):>10.4f}")

    _sub("Properti Sel — State Akhir")
    print(f"  {'Sel':>4}  {'P (psia)':>10}  {'Bo':>8}  {'Bw':>8}  {'Bg':>8}  "
          f"{'μo (cp)':>8}  {'kro':>8}  {'krw':>8}  {'krg':>8}")
    for i, cell in enumerate(grid["cells"]):
        p  = state["p"][i]
        sw = state["sw"][i]
        sg = state["sg"][i]
        pr = cell_props(p, sw, sg)
        print(f"  {i+1:>4}  {p:>10.3f}  {pr['bo']:>8.4f}  {pr['bw']:>8.5f}  "
              f"{pr['bg']:>8.5f}  {pr['mu_o']:>8.3f}  {pr['kro']:>8.4f}  "
              f"{pr['krw']:>8.4f}  {pr['krg']:>8.4f}")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    grid = build_grid()
    run_simulation(grid)

import json

NB = r"c:\My Workspaces\venv.Python\SIMULASI RESERVOIR\workflow.ipynb"

# Raw outer string — safe: no \a, \b, \f, \r, \t, \v sequences that could make BEL chars.
# LaTeX inside uses r'...' inner strings to protect \partial, \delta etc.
NEW_SRC = r"""import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

jacobian = rm.assemble_jacobian(grid, state_n, state_k, dt)
n_cells  = len(grid['cells'])
J        = np.array(jacobian, dtype=float)
n        = 3 * n_cells

row_labels, col_labels = jacobian_labels(n_cells)
jacobian_df = pd.DataFrame(J, index=row_labels, columns=col_labels)

nnz  = int(np.count_nonzero(J))
J_nz = np.abs(J[J != 0])
df_jacobian_stats = pd.DataFrame([{
    'ukuran matriks': f'{n} x {n}',
    'n_cell': n_cells,
    'nnz (non-zero)': nnz,
    'density %': round(100 * nnz / n**2, 2),
    'max |J|': float(J_nz.max()) if len(J_nz) else 0.0,
    'min |J| (non-zero)': float(J_nz.min()) if len(J_nz) else 0.0,
}])
print("=== Statistik Jacobian ===")
display(df_jacobian_stats)

def diag_block(J, c0, N):
    r = [c0, N+c0, 2*N+c0]
    return pd.DataFrame(
        J[np.ix_(r, r)],
        index  =[f'dRo[{c0+1}]/d?', f'dRw[{c0+1}]/d?', f'dRg[{c0+1}]/d?'],
        columns=[f'?=p[{c0+1}]',    f'?=Sw[{c0+1}]',   f'?=Sg[{c0+1}]'],
    )

CENTER_CELL = 13   # pusat grid 5x5
print(f"\n=== Blok Diagonal 3x3 — Cell {CENTER_CELL} (pusat, self-coupling) ===")
display(diag_block(J, CENTER_CELL - 1, n_cells))

# ── Permutasi ke cell-major (unknown per cell: p,Sw,Sg | residual per cell: Ro,Rw,Rg) ─
# perm[k] = posisi di J-original untuk baris/kolom ke-k di J_cm
# urutan: Ro1,Rw1,Rg1 | Ro2,Rw2,Rg2 | ... (untuk baris)
#          p1,Sw1,Sg1  | p2,Sw2,Sg2  | ... (untuk kolom)
perm     = [alpha * n_cells + c for c in range(n_cells) for alpha in range(3)]
J_cm     = J[np.ix_(perm, perm)]
J_abs_cm = np.abs(J_cm)

conn_pairs_0 = list(zip(
    df_connections['from_cell'].astype(int) - 1,
    df_connections['to_cell'].astype(int) - 1,
))

BG, TC, GC = '#0d1117', '#c9d1d9', '#21262d'
C_DIAG = '#ffd93d'
C_CONN = '#06d6a0'
C_SEP  = '#ff4444'    # merah — separator antar cell

# ── Tick labels: setiap cell menampilkan 3 unknown (X) / 3 residual (Y) ─────
x_lbl = []
y_lbl = []
for c in range(n_cells):
    x_lbl += [f'p·{c+1}', f'Sw·{c+1}', f'Sg·{c+1}']
    y_lbl += [f'Ro·{c+1}', f'Rw·{c+1}', f'Rg·{c+1}']

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: Heatmap + Sparsity  (cell-major, X=unknown, Y=residual)
# ─────────────────────────────────────────────────────────────────────────────
fig, (ax_h, ax_s) = plt.subplots(1, 2, figsize=(24, 10))
fig.patch.set_facecolor(BG)
for ax in (ax_h, ax_s):
    ax.set_facecolor(BG)
    for sp in ax.spines.values(): sp.set_color(GC)
    ax.tick_params(colors=TC, labelsize=4.5)

# ── Heatmap (log|J|) ─────────────────────────────────────────────────────────
J_log  = np.where(J_abs_cm > 1e-30, np.log10(J_abs_cm), np.nan)
cmap_h = plt.cm.plasma.copy(); cmap_h.set_bad(BG)
vmin   = np.nanmin(J_log) if not np.all(np.isnan(J_log)) else -10
vmax   = np.nanmax(J_log) if not np.all(np.isnan(J_log)) else 10

im = ax_h.imshow(J_log, cmap=cmap_h, aspect='auto',
                 interpolation='nearest', vmin=vmin, vmax=vmax)

# Garis merah pemisah antar cell (setiap 3 baris/kolom)
for t in range(3, n, 3):
    ax_h.axhline(t - 0.5, color=C_SEP, lw=1.0, zorder=5, alpha=0.85)
    ax_h.axvline(t - 0.5, color=C_SEP, lw=1.0, zorder=5, alpha=0.85)

# Blok diagonal (self-coupling) — kuning
for c in range(n_cells):
    lw_r = 2.5 if (c + 1) == CENTER_CELL else 1.0
    ax_h.add_patch(mpatches.Rectangle(
        (3*c - 0.5, 3*c - 0.5), 3, 3,
        linewidth=lw_r, edgecolor=C_DIAG, facecolor='none', zorder=6))

# Off-diagonal (koneksi)
for (ci, cj) in conn_pairs_0:
    for (ry, cx) in [(ci, cj), (cj, ci)]:
        ax_h.add_patch(mpatches.Rectangle(
            (3*cx - 0.5, 3*ry - 0.5), 3, 3,
            linewidth=0.8, edgecolor=C_CONN, facecolor='none', zorder=4, alpha=0.7))

cbar = fig.colorbar(im, ax=ax_h, shrink=0.85, pad=0.02)
cbar.set_label('log10|J|', color=TC, fontsize=9)
cbar.ax.yaxis.set_tick_params(color=TC, labelsize=8)
plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TC)
cbar.outline.set_edgecolor(GC)

ax_h.set_xticks(range(n))
ax_h.set_xticklabels(x_lbl, fontsize=4.2, color=TC, rotation=90, ha='center')
ax_h.set_yticks(range(n))
ax_h.set_yticklabels(y_lbl, fontsize=4.2, color=TC)

# Warnai label p (kolom 0 tiap block) lebih terang
for idx, lbl in enumerate(ax_h.get_xticklabels()):
    if idx % 3 == 0:
        lbl.set_color('#58a6ff')
        lbl.set_fontweight('bold')
for idx, lbl in enumerate(ax_h.get_yticklabels()):
    if idx % 3 == 0:
        lbl.set_color('#ff9944')
        lbl.set_fontweight('bold')

ax_h.set_xlabel('Unknown per cell  [ p | Sw | Sg ]', color=TC, fontsize=9)
ax_h.set_ylabel('Residual per cell  [ Ro | Rw | Rg ]', color=TC, fontsize=9)
ax_h.set_title(
    f'Jacobian {n}x{n} — Heatmap log|J|  (cell-major)\n'
    f'Garis merah = batas antar cell  |  Kuning = diagonal (self)  |  Hijau = koneksi',
    color=TC, fontsize=10, fontweight='bold', pad=8)

# ── Sparsity Pattern ──────────────────────────────────────────────────────────
J_bool = (J_abs_cm > 1e-30).astype(float)
ax_s.imshow(J_bool, cmap='Blues', aspect='auto',
            interpolation='nearest', vmin=0, vmax=1.5)

for t in range(3, n, 3):
    ax_s.axhline(t - 0.5, color=C_SEP, lw=1.0, zorder=5, alpha=0.85)
    ax_s.axvline(t - 0.5, color=C_SEP, lw=1.0, zorder=5, alpha=0.85)

fs_cell = 7 if n_cells <= 16 else 5.5
for c in range(n_cells):
    lw_r = 2.5 if (c + 1) == CENTER_CELL else 1.2
    ax_s.add_patch(mpatches.Rectangle(
        (3*c - 0.5, 3*c - 0.5), 3, 3,
        linewidth=lw_r, edgecolor=C_DIAG, facecolor='none', zorder=6))
    _clr = '#ff6b6b' if (c + 1) == CENTER_CELL else C_DIAG
    ax_s.text(3*c + 1, 3*c + 1, f'{c+1}',
              ha='center', va='center', fontsize=fs_cell,
              fontweight='bold', color=_clr, zorder=7)

seen_pairs = set()
for (ci, cj) in conn_pairs_0:
    key = (min(ci, cj), max(ci, cj))
    if key in seen_pairs: continue
    seen_pairs.add(key)
    for (ry, cx) in [(ci, cj), (cj, ci)]:
        ax_s.text(3*cx + 1, 3*ry + 1, 'x',
                  ha='center', va='center', fontsize=fs_cell,
                  color=C_CONN, fontweight='bold', zorder=7)

ax_s.set_xticks(range(n))
ax_s.set_xticklabels(x_lbl, fontsize=4.2, color=TC, rotation=90, ha='center')
ax_s.set_yticks(range(n))
ax_s.set_yticklabels(y_lbl, fontsize=4.2, color=TC)

for idx, lbl in enumerate(ax_s.get_xticklabels()):
    if idx % 3 == 0:
        lbl.set_color('#58a6ff')
        lbl.set_fontweight('bold')
for idx, lbl in enumerate(ax_s.get_yticklabels()):
    if idx % 3 == 0:
        lbl.set_color('#ff9944')
        lbl.set_fontweight('bold')

ax_s.set_xlabel('Unknown per cell  [ p | Sw | Sg ]', color=TC, fontsize=9)
ax_s.set_ylabel('Residual per cell  [ Ro | Rw | Rg ]', color=TC, fontsize=9)
ax_s.legend(handles=[
    mpatches.Patch(facecolor='#2171b5', label='Entry != 0'),
    mpatches.Patch(facecolor=BG,        label='Entry = 0'),
    mpatches.Patch(facecolor='none', edgecolor=C_DIAG, lw=1.5, label='Diagonal (self-coupling)'),
    mpatches.Patch(facecolor='none', edgecolor=C_CONN, lw=1.5, label='Off-diag (koneksi)'),
    mpatches.Patch(facecolor='none', edgecolor=C_SEP,  lw=1.5, label='Garis merah = batas cell'),
], fontsize=7.5, loc='upper right',
   facecolor='#0d1117', edgecolor=GC, labelcolor=TC)
ax_s.set_title(
    f'Sparsity Pattern {n}x{n}  (cell-major)\n'
    f'Angka = nomor cell  |  x hijau = koneksi  |  Merah tebal = cell {CENTER_CELL} (tengah)',
    color=TC, fontsize=10, fontweight='bold', pad=8)

fig.suptitle(
    f'Step 4 — Jacobian  {n_cells} cell x 3 fasa = {n}x{n}\n'
    f'Kolom (X) = unknown per cell: p | Sw | Sg   |   Baris (Y) = residual per cell: Ro | Rw | Rg\n'
    f'Garis merah = pemisah blok antar cell',
    color=TC, fontsize=11, fontweight='bold')
plt.tight_layout()
plt.show()

# ─────────────────────────────────────────────────────────────────────────────
# Figure 2: 9 Kemungkinan — Blok 3x3 Diagonal Cell 13 (pusat)
# J_ii = dR^(i)/dx^(i)  untuk cell itu sendiri
# ─────────────────────────────────────────────────────────────────────────────
c0      = CENTER_CELL - 1
_r_idx  = [3*c0, 3*c0+1, 3*c0+2]
J_block = J_cm[np.ix_(_r_idx, _r_idx)]

_ROW_LBL = [r'$\partial R_o$', r'$\partial R_w$', r'$\partial R_g$']
_COL_LBL = [r'$/\partial p$', r'$/\partial S_w$', r'$/\partial S_g$']
_DESCS   = [
    ['Bo, mu_o berubah\n-> Mo & akum So/Bo',   'kro turun (So turun)',       'kro turun (So turun)'],
    ['Bw, mu_w berubah\n-> Mw & akum Sw/Bw',   'krw naik + akum naik\n-> diagonal dominan', 'krw sedikit berubah'],
    ['Bg, Rso berubah\n-> elemen terbesar',      'Rso*So turun\n(coupling tdk langsung)',      'krg naik + Sg/Bg naik\n+ Rso*So turun\n-> paling kompleks'],
]

fig2, ax2 = plt.subplots(figsize=(14, 7))
fig2.patch.set_facecolor(BG); ax2.set_facecolor(BG)
for sp in ax2.spines.values(): sp.set_color(GC)
ax2.axis('off')

CW, CH, GAP = 4.0, 2.1, 0.25

for ri in range(3):
    for ci in range(3):
        val = J_block[ri, ci]
        x0  = ci * (CW + GAP)
        y0  = (2 - ri) * (CH + GAP)

        _is_diag = ri == ci
        _is_nz   = abs(val) > 1e-30
        _fc = '#ffd93d12' if _is_diag else ('#ff6b6b08' if _is_nz else '#ffffff04')
        _ec = C_DIAG if _is_diag else ('#3a5a8a' if _is_nz else '#2a3a4a')
        _lw = 2.2 if _is_diag else (0.9 if _is_nz else 0.4)

        ax2.add_patch(mpatches.FancyBboxPatch(
            (x0, y0), CW, CH, boxstyle='round,pad=0.1',
            facecolor=_fc, edgecolor=_ec, lw=_lw, zorder=2))

        _vs = f'{val:.5e}' if _is_nz else '0'
        _vc = C_DIAG if _is_diag else (TC if _is_nz else '#444444')
        ax2.text(x0 + CW/2, y0 + CH*0.70, _vs,
                 ha='center', va='center', fontsize=10, fontweight='bold',
                 color=_vc, family='monospace', zorder=3)

        ax2.text(x0 + CW/2, y0 + CH*0.28, _DESCS[ri][ci],
                 ha='center', va='center', fontsize=7.5, color='#aaaaaa',
                 linespacing=1.4, zorder=3)

for ri, rl in enumerate(_ROW_LBL):
    y0 = (2 - ri) * (CH + GAP) + CH/2
    ax2.text(-0.25, y0, rl, ha='right', va='center', fontsize=12,
             color='#ff6b6b', fontweight='bold')

for ci, cl in enumerate(_COL_LBL):
    x0 = ci * (CW + GAP) + CW/2
    ax2.text(x0, 3*(CH + GAP) + 0.1, cl, ha='center', va='bottom',
             fontsize=12, color='#06d6a0', fontweight='bold')

ax2.set_xlim(-1.9, 3*(CW + GAP) + 0.3)
ax2.set_ylim(-0.4, 3*(CH + GAP) + 0.75)
ax2.set_title(
    f'9 Kemungkinan Turunan Parsial — Blok Diagonal Cell {CENTER_CELL} (Pusat Grid {n_cells})\n'
    r'$J_{ii} = \partial R^{(i)} / \partial x^{(i)}$'
    r'   —   dR/dp  |  dR/dSw  |  dR/dSg',
    color=TC, fontsize=11, fontweight='bold', pad=10)
plt.tight_layout()
plt.show()

print("\n=== Potongan Jacobian — 3 cell pertama x 3 cell pertama (9x9) ===")
display(jacobian_df.iloc[:9, :9])
"""

# ─── Patch notebook ───────────────────────────────────────────────────────────
with open(NB, 'r', encoding='utf-8') as f:
    nb = json.load(f)

CELL_ID = 'aef0691a'
found = False
for cell in nb['cells']:
    if cell.get('id') == CELL_ID:
        lines = NEW_SRC.split('\n')
        cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
        cell['outputs'] = []
        cell['execution_count'] = None
        found = True
        break

if not found:
    print("ERROR: cell not found")
else:
    with open(NB, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("Patched aef0691a OK")

    # Verify: no BEL chars
    src_check = NEW_SRC
    bel = src_check.count(chr(7))
    print(f"BEL chars: {bel}")
    print(f"Lines: {len(NEW_SRC.splitlines())}")

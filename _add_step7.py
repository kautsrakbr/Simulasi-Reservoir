import json, uuid

NB = r"c:\My Workspaces\venv.Python\SIMULASI RESERVOIR\workflow.ipynb"

# ─── Markdown header ──────────────────────────────────────────────────────────
STEP7_MD = """\
## Step 7 — Final State: Semua Properti Per Cell

Setelah Newton converge, hitung dan tampilkan **semua properti PVT + saturasi** \
untuk setiap cell di grid `NX×NY`.

| Properti | Sumber | Keterangan |
|----------|--------|------------|
| `p (psia)` | state | Tekanan per cell |
| `So, Sw, Sg` | state | Saturasi 3 fasa |
| `Bo, Bw, Bg` | PVT table | Formation volume factor |
| `mu_o, mu_w, mu_g` | PVT table | Viskositas (cp) |
| `kro, krw, krg` | Rock table | Permeabilitas relatif |
| `lam_o, lam_w, lam_g` | derived | Mobilitas = kr / mu |
| `rho_o, rho_w, rho_g` | derived | Densitas reservoir (lbm/ft³) |
| `Pcow, Pcgw` | Rock table | Tekanan kapilari |
"""

# ─── Code cell source ─────────────────────────────────────────────────────────
# NOTE: use r-string so \n, \t etc. inside are NOT interpreted
STEP7_CODE = r"""import matplotlib.pyplot as plt
import numpy as np

# ── Hitung semua properti final per cell (state konvergen Step 6) ─────────────
df_fin = evaluate_state(grid, state_step_1).copy()
df_fin = df_fin.merge(df_cells[['cell', 'i_index', 'j_index']], on='cell')

NX_ = rm.NX
NY_ = rm.NY
N_  = NX_ * NY_

# ── Properti yang diplot sebagai heatmap (4 kolom x 4 baris = 16 plot) ───────
PROPS = [
    ('pressure_psia', 'p (psia)',      'plasma'),
    ('so',            'So',            'YlOrRd'),
    ('sw',            'Sw',            'Blues'),
    ('sg',            'Sg',            'Greens'),
    ('bo',            'Bo (rb/stb)',   'autumn'),
    ('bw',            'Bw (rb/stb)',   'winter'),
    ('bg',            'Bg (rcf/scf)', 'copper'),
    ('mu_o',          'mu_o (cp)',     'hot'),
    ('mu_w',          'mu_w (cp)',     'cool'),
    ('mu_g',          'mu_g (cp)',     'viridis'),
    ('kro',           'kro',           'YlOrRd'),
    ('krw',           'krw',           'Blues'),
    ('krg',           'krg',           'Greens'),
    ('lam_o',         'lam_o (1/cp)', 'plasma'),
    ('lam_w',         'lam_w (1/cp)', 'plasma'),
    ('lam_g',         'lam_g (1/cp)', 'plasma'),
]

BG, TC, GC = '#0d1117', '#c9d1d9', '#21262d'
NCOLS = 4
NROWS = (len(PROPS) + NCOLS - 1) // NCOLS

fig, axes = plt.subplots(NROWS, NCOLS, figsize=(NCOLS * 4.5, NROWS * 4.2))
fig.patch.set_facecolor(BG)
axes_flat = axes.flatten()

for idx, (col, label, cmap) in enumerate(PROPS):
    ax = axes_flat[idx]
    ax.set_facecolor(BG)

    mat = np.full((NY_, NX_), np.nan)
    for _, r in df_fin.iterrows():
        mat[int(r['j_index']), int(r['i_index'])] = r[col]

    vlo, vhi = float(np.nanmin(mat)), float(np.nanmax(mat))
    if vlo == vhi:
        vhi = vlo + 1e-9

    im = ax.imshow(mat, cmap=cmap, aspect='equal', origin='upper',
                   vmin=vlo, vmax=vhi)

    for gj in range(NY_):
        for gi in range(NX_):
            v   = mat[gj, gi]
            cno = gj * NX_ + gi + 1
            if abs(v) >= 100:
                vtxt = f'{v:.1f}'
            elif abs(v) < 0.001:
                vtxt = f'{v:.2e}'
            elif abs(v) < 0.01:
                vtxt = f'{v:.5f}'
            elif abs(v) < 0.1:
                vtxt = f'{v:.5f}'
            elif abs(v) < 10:
                vtxt = f'{v:.4f}'
            else:
                vtxt = f'{v:.2f}'
            # nilai
            ax.text(gi, gj + 0.15, vtxt, ha='center', va='center',
                    fontsize=6.5, color='white', fontweight='bold')
            # label cell
            ax.text(gi, gj - 0.27, f'C{cno}', ha='center', va='center',
                    fontsize=5.5, color='#ffffff99')

    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.tick_params(colors=TC, labelsize=6)
    cb.outline.set_edgecolor(GC)

    ax.set_title(label, color=TC, fontsize=9, fontweight='bold', pad=5)
    ax.set_xticks(range(NX_))
    ax.set_xticklabels([f'i={v}' for v in range(NX_)], color=TC, fontsize=6)
    ax.set_yticks(range(NY_))
    ax.set_yticklabels([f'j={v}' for v in range(NY_)], color=TC, fontsize=6)
    for sp in ax.spines.values():
        sp.set_color(GC)

for idx in range(len(PROPS), NROWS * NCOLS):
    axes_flat[idx].set_visible(False)

fig.suptitle(
    f'Step 7 — Final State: 16 Properti Per Cell  (Grid {NX_}x{NY_}, {N_} sel, dt={rm.DT_INITIAL:.0f} hari)',
    color=TC, fontsize=11, fontweight='bold', y=1.004
)
plt.tight_layout()
plt.show()

# ── Tabel lengkap: semua properti numerik per cell ───────────────────────────
_COLS = ['cell', 'i_index', 'j_index',
         'pressure_psia', 'so', 'sw', 'sg',
         'bo', 'bw', 'bg',
         'mu_o', 'mu_w', 'mu_g',
         'kro', 'krw', 'krg',
         'lam_o', 'lam_w', 'lam_g',
         'rho_o', 'rho_w', 'rho_g',
         'pcow', 'pcgw']

_REN = {
    'cell': 'Cell', 'i_index': 'i', 'j_index': 'j',
    'pressure_psia': 'p (psia)', 'so': 'So', 'sw': 'Sw', 'sg': 'Sg',
    'bo': 'Bo', 'bw': 'Bw', 'bg': 'Bg',
    'mu_o': 'mu_o', 'mu_w': 'mu_w', 'mu_g': 'mu_g',
    'kro': 'kro', 'krw': 'krw', 'krg': 'krg',
    'lam_o': 'lam_o', 'lam_w': 'lam_w', 'lam_g': 'lam_g',
    'rho_o': 'rho_o', 'rho_w': 'rho_w', 'rho_g': 'rho_g',
    'pcow': 'Pcow', 'pcgw': 'Pcgw',
}

_FMT = {
    'p (psia)': '{:.2f}',
    'So': '{:.5f}', 'Sw': '{:.5f}', 'Sg': '{:.5f}',
    'Bo': '{:.6f}', 'Bw': '{:.6f}', 'Bg': '{:.6f}',
    'mu_o': '{:.5f}', 'mu_w': '{:.5f}', 'mu_g': '{:.5f}',
    'kro': '{:.5f}', 'krw': '{:.5f}', 'krg': '{:.5f}',
    'lam_o': '{:.6f}', 'lam_w': '{:.6f}', 'lam_g': '{:.6f}',
    'rho_o': '{:.3f}', 'rho_w': '{:.3f}', 'rho_g': '{:.3f}',
    'Pcow': '{:.4f}', 'Pcgw': '{:.4f}',
}

_GRAD = {
    'p (psia)': 'plasma',
    'So': 'YlOrRd', 'Sw': 'Blues', 'Sg': 'Greens',
    'kro': 'YlOrRd', 'krw': 'Blues', 'krg': 'Greens',
}

df_tbl = df_fin[_COLS].rename(columns=_REN)

_stl = df_tbl.style.format(_FMT)
for _c, _cm in _GRAD.items():
    _stl = _stl.background_gradient(subset=[_c], cmap=_cm, axis=0)

_stl = (
    _stl
    .set_properties(**{
        'background-color': '#0d1117',
        'color': '#c9d1d9',
        'border': '1px solid #21262d',
        'text-align': 'center',
        'font-size': '11px',
        'padding': '4px 8px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#161b22'),
            ('color', '#58a6ff'),
            ('font-weight', 'bold'),
            ('border', '1px solid #21262d'),
            ('text-align', 'center'),
            ('font-size', '11px'),
        ]},
        {'selector': 'caption', 'props': [
            ('caption-side', 'top'),
            ('color', '#c9d1d9'),
            ('font-size', '12px'),
            ('font-weight', 'bold'),
            ('padding', '8px'),
        ]},
    ])
    .set_caption(
        f'Tabel Semua Properti PVT Per Cell  |  Grid {NX_}x{NY_}  |  {N_} sel  |  dt={rm.DT_INITIAL:.0f} hari'
    )
)

print(f'Grid {NX_}x{NY_} = {N_} sel  |  dt = {rm.DT_INITIAL:.0f} hari  |  State: konvergen')
display(_stl)
"""

# ─── Build notebook cells ─────────────────────────────────────────────────────
def src_to_list(text: str) -> list:
    """Split multi-line source into list-of-lines (Jupyter format)."""
    lines = text.split('\n')
    result = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            result.append(line + '\n')
        else:
            if line:  # don't add trailing empty line
                result.append(line)
    return result

md_cell = {
    "cell_type": "markdown",
    "id": uuid.uuid4().hex[:8],
    "metadata": {},
    "source": src_to_list(STEP7_MD),
}

code_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": uuid.uuid4().hex[:8],
    "metadata": {},
    "outputs": [],
    "source": src_to_list(STEP7_CODE),
}

with open(NB, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Remove old Step7 cells if re-running
nb['cells'] = [c for c in nb['cells']
               if '## Step 7' not in ''.join(c.get('source', []))]

nb['cells'].append(md_cell)
nb['cells'].append(code_cell)

with open(NB, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f'Added Step 7: markdown {md_cell["id"]}, code {code_cell["id"]}')
print(f'Total cells: {len(nb["cells"])}')

# Quick verify: check no BEL in new code cell
src_check = ''.join(code_cell['source'])
bel = src_check.count(chr(7))
print(f'BEL chars in new cell: {bel}')
print('STEP7_CODE line count:', len([l for l in STEP7_CODE.split(chr(10)) if l.strip()]))

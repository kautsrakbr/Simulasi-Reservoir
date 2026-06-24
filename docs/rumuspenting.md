# Ringkasan Rumus — Reservoir Simulator Black Oil (Fully Implicit)

---

## 1. Unknown & Constraint

Tiap cell punya **3 unknown**: `p`, `Sw`, `Sg`

Constraint saturasi (selalu harus dipenuhi):

```
So = 1 - Sw - Sg
```

Untuk 9 cell → total **27 unknown**, dan **27 residual** yang harus = 0.

---

## 2. Transmissibility & Mobility

### Transmissibility antar cell (geometri)

$$T_{12} = 0.00603 \cdot \frac{2k_1 k_2}{k_1 + k_2} \cdot \frac{A}{\Delta x}$$

- `k` = permeabilitas (mD)
- `A` = luas penampang (ft²)
- `Δx` = jarak antar cell (ft)
- `0.00603` = faktor konversi field unit

### Mobility tiap fasa

$$M_o = \frac{k_{ro}(S_o)}{\mu_o \cdot B_o}, \quad M_w = \frac{k_{rw}(S_w)}{\mu_w \cdot B_w}, \quad M_g = \frac{k_{rg}(S_g)}{\mu_g \cdot B_g}$$

---

## 3. Flow Rate Antar Cell

Flow rate fasa dari cell j ke cell i:

$$q_{o,ji} = T_{ij} \cdot M_o \cdot (p_j - p_i)$$

$$q_{w,ji} = T_{ij} \cdot M_w \cdot (p_j - p_i)$$

$$q_{g,ji} = T_{ij} \cdot M_g \cdot (p_j - p_i)$$

- Positif → flow masuk ke cell i
- Negatif → flow keluar dari cell i
- Kalau `p_j = p_i` → tidak ada flow (Jacobian off-diagonal = 0)

---

## 4. Flow Rate Produksi Sumur

### Well Index (geometri sumur)

$$WI = \frac{2\pi k h}{\ln(r_e / r_w)}$$

### Flowrate produksi (rumus dasar, tanpa Peaceman correction)

$$q_o = WI \cdot \frac{k_{ro}}{\mu_o B_o} \cdot (p_{cell} - p_{wf})$$

$$q_w = WI \cdot \frac{k_{rw}}{\mu_w B_w} \cdot (p_{cell} - p_{wf})$$

$$q_g = WI \cdot \frac{k_{rg}}{\mu_g B_g} \cdot (p_{cell} - p_{wf}) + R_{so} \cdot q_o$$

- `p_cell` = tekanan cell tempat sumur berada
- `p_wf` = wellbore flowing pressure (given/input)
- `qg` punya dua suku: **gas bebas** + **gas terlarut** yang ikut minyak

### Undersaturated vs Saturated

| Kondisi | p vs bubble point | Sg | krg | qg |
|---------|------------------|----|-----|----|
| Undersaturated | p > pb | = 0 | = 0 | hanya Rso·qo |
| Saturated | p < pb | > 0 | > 0 | gas bebas + Rso·qo |

Rumus flowrate **sama persis** — yang berbeda hanya nilai krg dan Sg yang otomatis nol atau tidak nol tergantung kondisi.

---

## 5. Residual Per Cell (Material Balance)

### Residual Oil

$$R_o = \sum_j T_{ij} \cdot M_o^{n+1} \cdot (p_j - p_i)^{n+1} - \frac{1}{\Delta t}\left[\frac{V_p S_o^{n+1}}{B_o^{n+1}} - \frac{V_p S_o^n}{B_o^n}\right] - q_o$$

### Residual Water

$$R_w = \sum_j T_{ij} \cdot M_w^{n+1} \cdot (p_j - p_i)^{n+1} - \frac{1}{\Delta t}\left[\frac{V_p S_w^{n+1}}{B_w^{n+1}} - \frac{V_p S_w^n}{B_w^n}\right]$$

### Residual Gas

$$R_g = \sum_j T_{ij} \cdot M_g^{n+1} \cdot (p_j - p_i)^{n+1} - \frac{1}{\Delta t}\left[\frac{V_p S_g^{n+1}}{B_g^{n+1}} + R_{so}^{n+1}\frac{V_p S_o^{n+1}}{B_o^{n+1}} - \frac{V_p S_g^n}{B_g^n} - R_{so}^n\frac{V_p S_o^n}{B_o^n}\right] - q_g$$

**Catatan:**
- Superscript `n` = nilai timestep lama (known)
- Superscript `n+1` = nilai timestep baru (unknown, dicari Newton)
- Summasi `Σj` = jumlahkan dari semua cell tetangga j
- `qo` dan `qg` hanya ada di cell sumur
- Rg punya **dua suku akumulasi**: gas bebas (`Sg/Bg`) + gas terlarut (`Rso·So/Bo`)

---

## 6. Jacobian — 9 Rumus Turunan Parsial

Jacobian dihitung numerik via **finite difference perturbasi**.

Ingat selalu: waktu Sw atau Sg diperturb, **So ikut berubah** karena:
```
So* = 1 - (Sw + ΔSw) - Sg     ← waktu perturb Sw
So* = 1 - Sw - (Sg + ΔSg)     ← waktu perturb Sg
So* = So                        ← waktu perturb p (So tidak berubah)
```

---

### Kolom 1: Perturb **p**

So tidak ikut berubah. Yang berubah: properti PVT (Bo, μo, Bg, Rso, Bw, μw).

**∂Ro/∂p**

$$\frac{\partial R_o}{\partial p} = \frac{R_o(p+\Delta p,\ Sw,\ Sg,\ So) - R_o(p,\ Sw,\ Sg,\ So)}{\Delta p}$$

Yang berubah: `Bo(p)`, `μo(p)` → mobility Mo berubah, akumulasi `VpSo/Bo` berubah.

---

**∂Rw/∂p**

$$\frac{\partial R_w}{\partial p} = \frac{R_w(p+\Delta p,\ Sw,\ Sg,\ So) - R_w(p,\ Sw,\ Sg,\ So)}{\Delta p}$$

Yang berubah: `Bw(p)`, `μw(p)`. Nilainya kecil karena air hampir incompressible.

---

**∂Rg/∂p**

$$\frac{\partial R_g}{\partial p} = \frac{R_g(p+\Delta p,\ Sw,\ Sg,\ So) - R_g(p,\ Sw,\ Sg,\ So)}{\Delta p}$$

Yang berubah: `Bg(p)` (sangat sensitif) dan `Rso(p)`. Ini elemen **terbesar** di kolom p.

---

### Kolom 2: Perturb **Sw** → So\* = So − ΔSw

So ikut turun. Yang berubah: kro(So\*) dan krw(Sw+ΔSw).

**∂Ro/∂Sw**

$$\frac{\partial R_o}{\partial S_w} = \frac{R_o(p,\ Sw+\Delta Sw,\ Sg,\ \mathbf{So^*}) - R_o(p,\ Sw,\ Sg,\ So)}{\Delta Sw}$$

Yang berubah: `kro(So*)` turun karena So turun → minyak makin susah mengalir.

---

**∂Rw/∂Sw**

$$\frac{\partial R_w}{\partial S_w} = \frac{R_w(p,\ Sw+\Delta Sw,\ Sg,\ \mathbf{So^*}) - R_w(p,\ Sw,\ Sg,\ So)}{\Delta Sw}$$

Yang berubah: `krw(Sw+ΔSw)` naik + akumulasi `VpSw/Bw` naik. Ini **elemen diagonal dominan** baris water.

---

**∂Rg/∂Sw**

$$\frac{\partial R_g}{\partial S_w} = \frac{R_g(p,\ Sw+\Delta Sw,\ Sg,\ \mathbf{So^*}) - R_g(p,\ Sw,\ Sg,\ So)}{\Delta Sw}$$

Yang berubah: suku `Rso·So*/Bo` turun karena So\* turun. Coupling tidak langsung Sw → So → gas solution.

---

### Kolom 3: Perturb **Sg** → So\* = So − ΔSg

So ikut turun. Yang berubah: kro(So\*) dan krg(Sg+ΔSg).

**∂Ro/∂Sg**

$$\frac{\partial R_o}{\partial S_g} = \frac{R_o(p,\ Sw,\ Sg+\Delta Sg,\ \mathbf{So^*}) - R_o(p,\ Sw,\ Sg,\ So)}{\Delta Sg}$$

Yang berubah: `kro(So*)` turun karena So turun.

---

**∂Rw/∂Sg**

$$\frac{\partial R_w}{\partial S_g} = \frac{R_w(p,\ Sw,\ Sg+\Delta Sg,\ \mathbf{So^*}) - R_w(p,\ Sw,\ Sg,\ So)}{\Delta Sg}$$

Yang berubah: `krw` sedikit berubah. Nilainya biasanya kecil.

---

**∂Rg/∂Sg** ← *dilingkarin dosen karena paling kompleks*

$$\frac{\partial R_g}{\partial S_g} = \frac{R_g(p,\ Sw,\ Sg+\Delta Sg,\ \mathbf{So^*}) - R_g(p,\ Sw,\ Sg,\ So)}{\Delta Sg}$$

Tiga hal sekaligus berubah:
1. `krg(Sg+ΔSg)` **naik** → gas makin mudah mengalir
2. Akumulasi `Sg/Bg` **naik** langsung
3. `Rso·So*/Bo` **turun** karena So\* turun

Tiga pengaruh berlawanan arah → paling susah dianalitik → alasan utama pakai perturbasi numerik.

---

### Ringkasan 9 Elemen

| | ∂/∂p | ∂/∂Sw | ∂/∂Sg |
|--|------|--------|--------|
| **Ro** | Bo, μo berubah | kro↓ (So↓) | kro↓ (So↓) |
| **Rw** | Bw, μw berubah | krw↑ + akumulasi↑ | krw sedikit berubah |
| **Rg** | Bg, Rso berubah besar | Rso·So↓ | krg↑ + Sg/Bg↑ + Rso·So↓ |

---

## 7. Newton-Raphson — Persamaan Linear

Dari 9 elemen tadi, blok 3×3 per cell i:

$$J_{ii} = \begin{bmatrix} \partial R_o/\partial p & \partial R_o/\partial S_w & \partial R_o/\partial S_g \\ \partial R_w/\partial p & \partial R_w/\partial S_w & \partial R_w/\partial S_g \\ \partial R_g/\partial p & \partial R_g/\partial S_w & \partial R_g/\partial S_g \end{bmatrix}$$

Persamaan yang di-solve tiap iterasi Newton:

$$J \cdot \delta x = -R$$

Dimana:

$$\delta x = \begin{bmatrix} \delta p \\ \delta S_w \\ \delta S_g \end{bmatrix}, \quad R = \begin{bmatrix} R_o \\ R_w \\ R_g \end{bmatrix}$$

Update setelah solve:

$$p^{k+1} = p^k + \delta p$$
$$S_w^{k+1} = S_w^k + \delta S_w$$
$$S_g^{k+1} = S_g^k + \delta S_g$$

---

## 8. Update Per Cell — Primary Variables & PVT

Setelah solve `J·δx = -R`, vektor koreksi δx berisi 27 nilai. Tiap cell ambil koreksi miliknya sendiri dan **langsung update semua properti**:

```
untuk cell i = 1, 2, 3, ..., 9:

    # --- primary variables ---
    p[i]  = p[i]  + δp[i]
    Sw[i] = Sw[i] + δSw[i]
    Sg[i] = Sg[i] + δSg[i]
    So[i] = 1 - Sw[i] - Sg[i]      ← constraint, bukan unknown

    # --- PVT (fungsi tekanan p[i]) ---
    Bo[i]  = interp(tabel_Bo,  p[i])
    Bw[i]  = interp(tabel_Bw,  p[i])
    Bg[i]  = interp(tabel_Bg,  p[i])
    μo[i]  = interp(tabel_μo,  p[i])
    μw[i]  = interp(tabel_μw,  p[i])
    μg[i]  = interp(tabel_μg,  p[i])
    Rso[i] = interp(tabel_Rso, p[i])

    # --- relative permeability (fungsi saturasi) ---
    kro[i] = interp(tabel_kro, So[i])
    krw[i] = interp(tabel_krw, Sw[i])
    krg[i] = interp(tabel_krg, Sg[i])

    # --- mobility ---
    Mo[i] = kro[i] / (μo[i] * Bo[i])
    Mw[i] = krw[i] / (μw[i] * Bw[i])
    Mg[i] = krg[i] / (μg[i] * Bg[i])
```

**Kenapa semua harus di-update tiap iterasi?**
Karena residual dan Jacobian iterasi berikutnya pakai nilai PVT yang baru. Kalau tidak di-update, residual yang dihitung salah dan Newton tidak konvergen.

**Apa yang fungsi tekanan, apa yang fungsi saturasi?**

| Properti | Fungsi dari | Catatan |
|----------|------------|---------|
| Bo, Bw, Bg | p | Dari tabel PVT, interpolasi linear |
| μo, μw, μg | p | Dari tabel PVT |
| Rso | p | Gas terlarut dalam minyak, turun saat p turun |
| kro | So | Dari tabel kr |
| krw | Sw | Dari tabel kr |
| krg | Sg | Dari tabel kr |

---

## 9. Alur Lengkap Per Timestep

```
1. Tebakan awal:
   p^(k=0) = p^(n+1) - (ΔP/Δt_prev) · Δt

2. LOOP Newton (k = 0, 1, 2, ...):

   a. Update primary variables per cell:
      p[i] += δp[i],  Sw[i] += δSw[i],  Sg[i] += δSg[i]
      So[i] = 1 - Sw[i] - Sg[i]

   b. Update PVT per cell:
      Bo, Bw, Bg, μo, μw, μg, Rso  ← fungsi p[i]
      kro, krw, krg                  ← fungsi So, Sw, Sg
      Mo, Mw, Mg                     ← = kr / (μ·B)

   c. Hitung 27 residual: Ro, Rw, Rg tiap cell

   d. Cek konvergensi: |R| < toleransi? → selesai

   e. Hitung Jacobian 27×27 via perturbasi numerik
      (tiap perturbasi → PVT juga dihitung ulang!)

   f. Solve: J·δx = -R

   g. Cek dpMax, dSwMax, dSgMax → cutback Δt jika perlu

   h. Balik ke langkah a

3. t = t + Δt → lanjut timestep berikutnya
```

---

## 10. Konvergensi

Simulator berhenti iterasi Newton kalau **semua** constraint ini terpenuhi:

| Constraint | Keterangan |
|-----------|------------|
| `iter < MaxNewton` | Jumlah iterasi tidak boleh melebihi batas |
| `\|R\| < MaxResidErr` | Residual semua cell sudah cukup kecil |
| `\|δp\| < dpMax` | Koreksi tekanan tidak terlalu besar |
| `\|δSw\| < dSwMax` | Koreksi saturasi air tidak terlalu besar |
| `\|δSg\| < dSgMax` | Koreksi saturasi gas tidak terlalu besar |

Kalau tidak konvergen → `Δt = α · Δt` dengan `α < 1` (timestep cutback).
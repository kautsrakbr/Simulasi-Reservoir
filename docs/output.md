# Rangkuman Konsep Reservoir Simulator - Fully Implicit Black Oil

## 1. Apa itu Residual dan Jacobian?

### Residual
Residual adalah jawaban dari pertanyaan: **"seberapa salah solusi kita sekarang?"**

Residual merepresentasikan ketidakseimbangan massa di setiap cell — seberapa jauh kondisi saat ini dari yang seharusnya (konservasi massa). Kalau residual = 0, berarti konservasi massa terpenuhi sempurna dan iterasi selesai.

Di simulator Black Oil 3-phase, residual dihitung per phase per cell:

```
R_p = Δ(a_p · ΔΦ_p) ± q_p - (1/Δt) × [(VporeSp/Bp)^(n+1) - (VporeSp/Bp)^n]
```

Karena ada 3 phase (oil, water, gas) dan misalnya 25 cell (grid 5×5×1), maka total residual ada **75 nilai** (25 cell × 3 phase), berbentuk vektor 75×1.

Residual ada tiga komponen:
- **Ro** — residual oil
- **Rw** — residual water
- **Rg** — residual gas

Satuan residual adalah volume fluida yang tidak seimbang: **STB** untuk oil dan water, **Mscf** untuk gas. Kalau nilainya kecil (misal 10E-5), itu tanda bagus — ketidakseimbangan massanya sudah sangat kecil dan hampir konvergen.

### Jacobian
Jacobian adalah jawaban dari pertanyaan: **"kalau variabel kita ganggu sedikit, residual berubah berapa?"**

Jacobian adalah turunan parsial residual terhadap semua variabel (p, Sw, Sg). Bentuknya matrix — untuk 75 unknowns, ukurannya 75×75.

Hubungan Jacobian dan residual: **Jacobian adalah turunan dari residual**. Residual itu fungsinya, Jacobian itu kemiringannya.

Lebih tepatnya, nilai Jacobian adalah **perubahan residual dibagi perubahan variabelnya**:

```
J = (R(x + Δx) - R(x)) / Δx
```

Jadi bukan sekadar "perubahan residual" — tapi perubahan residual per unit perubahan variabel. Contoh: kalau pressure naik 1 psi dan residual oil berubah sebesar 29 STB, maka nilai Jacobian di posisi itu adalah 29 STB/psi. Itu yang keliatan di tabel Jacobian — angka -29 di diagonal artinya "setiap pressure naik 1 psi, residual oil turun 29 satuan."

---

## 2. Kenapa ada Ro, Rw, Rg — tapi tidak ada So?

Di simulator fully implicit, unknowns per cell ada 3: **p, Sw, Sg**. Untuk 3 unknowns dibutuhkan 3 persamaan — makanya residualnya Ro, Rw, dan Rg.

So tidak dijadikan unknown karena nilainya selalu bisa dihitung dari constraint:

```
So = 1 - Sw - Sg
```

Kalau So ikut diperturbasi, constraint total saturasi = 1 akan dilanggar. Makanya So hanya variabel turunan, bukan unknown yang disolve.

---

## 3. Perturbasi — Cara Menghitung Jacobian

Perturbasi artinya **ganggu sedikit** satu variabel, lalu lihat seberapa besar residual berubah. Sensitivitas itulah yang menjadi isi Jacobian.

Rumus perturbasi numerik:

```
∂R/∂p  = [R(p + Δp, Sw, Sg) - R(p, Sw, Sg)] / Δp
∂R/∂Sw = [R(p, Sw + ΔSw, Sg) - R(p, Sw, Sg)] / ΔSw
∂R/∂Sg = [R(p, Sw, Sg + ΔSg) - R(p, Sw, Sg)] / ΔSg
```

Karena ada 3 variabel per cell dan 25 cell = 75 unknowns, maka untuk mendapat satu Jacobian penuh dibutuhkan **75 kali perhitungan residual tambahan**.

**Penting:** Setiap kali perturbasi, semua properti fluida (Bo, Bg, Bw, μ, Rs) harus dihitung ulang di nilai yang sudah diperturbasi — bukan pakai nilai lama. Kalau lupa, Jacobian akan salah.

### Cara Cek Jacobian Sudah Benar

**1. Cek tanda**
- Diagonal harus **negatif** — kalau pressure satu cell naik, fluida keluar, residual cell itu turun
- Off-diagonal harus **positif** — fluida yang keluar masuk ke tetangga, residual tetangga naik

**2. Cek besaran diagonal**
Cell yang punya lebih banyak tetangga harus punya diagonal lebih besar (lebih negatif):
- Cell pojok (2 tetangga) → diagonal terkecil
- Cell tepi (3 tetangga) → diagonal sedang
- Cell tengah (4 tetangga) → diagonal terbesar

**3. Cek simetri matrix**
Di grid homogen, nilai di (C1 Ro, C2 dp) harus sama dengan (C2 Ro, C1 dp). Pengaruh C1 ke C2 harus sama dengan pengaruh C2 ke C1.

**4. Bandingkan dengan nilai analitik**
Turunan suku transmissibility T × (p1 - p2) terhadap p1 secara analitik hasilnya adalah T. Bandingkan nilai T itu dengan hasil perturbasi numerik. Kalau sama atau sangat dekat, implementasi perturbasi benar.

### Kenapa Blok Gas Nilainya Jauh Lebih Besar?

Di Jacobian, blok Rg terhadap dSg nilainya bisa sampai 10^7, jauh lebih besar dari blok oil. Ini karena gas sangat kompresibel — Bg sangat sensitif terhadap pressure. Perubahan pressure kecil langsung membuat residual gas berubah drastis.

---

## 4. Peran PVT dalam Residual dan Jacobian

PVT adalah jembatan antara pressure/saturasi dengan sifat fisik fluida. Tanpa PVT, residual tidak bisa dihitung.

Di dalam residual ada suku storage:

```
(Vpore × S) / B
```

B (Bo, Bw, Bg) diambil dari tabel PVT via interpolasi. Selain itu, viskositas (μ) dan Rs (gas terlarut di oil) juga dari PVT.

**Pengaruh PVT ke Jacobian:**
- Kolom dp → PVT paling berpengaruh, karena Bo, Bg, μ, Rs semuanya fungsi pressure
- Kolom dSw dan dSg → relative permeability lebih dominan, karena kr fungsi saturasi

Saat perturbasi numerik dipakai, turunan PVT tidak perlu dihitung eksplisit — efeknya sudah tertangkap otomatis karena Bo, Bg, μ, Rs ikut diinterpolasi ulang di nilai pressure yang sudah diperturbasi.

---

## 5. Alur Lengkap Simulasi

```
Kondisi Awal (p, Sw, Sg)
        ↓
Hitung Residual (Ro, Rw, Rg)
        ↓
Hitung Jacobian (via perturbasi)
        ↓
Solve: J · δx = -R
        ↓
Update variabel: x_baru = x_lama + δx
        ↓
Cek konvergensi — residual < toleransi?
    Tidak → balik ke hitung residual
    Ya → maju ke timestep berikutnya
```

### Kondisi Awal (Tebakan Awal)

Tebakan awal adalah nilai p, Sw, Sg di seluruh cell sebelum simulasi dimulai. Contoh:
- Tekanan referensi: 2500 psi di kedalaman 6500 ft
- Sw awal: 0.25
- Sg awal: 0.05
- So awal: 0.70 (dihitung otomatis)

Makin bagus tebakan awal, makin sedikit iterasi Newton yang dibutuhkan.

### Kenapa Butuh Iterasi Newton?

Karena persamaan reservoir **nonlinear** — ada relative permeability, kompresibilitas, PVT yang semua nonlinear terhadap p dan S.

Jacobian hanya pendekatan linear dari fungsi yang sebetulnya melengkung. Satu koreksi dari Jacobian belum tentu langsung menghasilkan residual = 0. Makanya harus diulang — tiap iterasi makin dekat ke solusi — sampai residual betul-betul di bawah toleransi.

**Analogi:** Dunia reservoir itu melengkung, Jacobian itu cuma penggaris lurus. Sekali pakai penggaris di fungsi yang melengkung, hasilnya hanya perkiraan. Harus diulang terus sampai konvergen.

---

## 6. Output Simulasi Per Timestep

Simulator tidak langsung prediksi 30 tahun sekaligus — dia maju pelan-pelan timestep by timestep. Tiap timestep Newton selesai konvergen, waktu simulasi maju Δt.

### Pengaturan Waktu Simulasi

Misalnya mau simulasi 30 tahun dengan Δt = 30 hari:

```
30 tahun × 365 hari = 10950 hari
10950 / 30 = 365 timestep
```

Dalam prakteknya Δt bersifat adaptif:
- Kalau Newton konvergen cepat → Δt diperbesar (lebih efisien)
- Kalau Newton susah konvergen → Δt diperkecil (lebih stabil)

Parameter yang perlu diinput di UI:
- Waktu total simulasi
- Δt awal
- Δt maksimum

### Output Per Cell (Per Timestep)

| Output | Satuan | Keterangan |
|--------|--------|------------|
| Tekanan p | psi | Hasil langsung dari solve Newton |
| Saturasi air Sw | fraction | Hasil langsung dari solve Newton |
| Saturasi gas Sg | fraction | Hasil langsung dari solve Newton |
| Saturasi minyak So | fraction | Dihitung dari 1 - Sw - Sg |

### Output Per Sumur (Per Timestep)

| Output | Satuan | Keterangan |
|--------|--------|------------|
| Flowrate oil | STB/day | Dihitung dari WI × kr/μB × (p_cell - BHP) |
| Flowrate water | STB/day | Sama seperti oil |
| Flowrate gas | Mscf/day | Sama seperti oil |
| Bottomhole pressure | psi | Input kondisi operasi sumur |
| Water cut | fraction | Qw / (Qo + Qw) |
| GOR | Mscf/STB | Qg / Qo |

**Catatan:** BHP (Bottomhole Pressure) adalah input yang ditentukan sendiri sebagai kondisi operasi sumur, bukan hasil solve Newton.

### Output Kumulatif (Akumulasi Dari Timestep 1)

| Output | Satuan | Cara Hitung |
|--------|--------|-------------|
| Np (kumulatif oil) | STB | Np = Np_sebelumnya + q_oil × Δt |
| Wp (kumulatif water) | STB | Wp = Wp_sebelumnya + q_water × Δt |
| Gp (kumulatif gas) | Mscf | Gp = Gp_sebelumnya + q_gas × Δt |
| Recovery Factor | fraction | RF = Np / OOIP |

### Visualisasi yang Wajib Ada di UI

1. **Kurva flowrate vs waktu** — keliatan kapan produksi mulai decline
2. **Kurva kumulatif vs waktu** — keliatan total recovery
3. **Kurva water cut vs waktu** — keliatan kapan air mulai masuk ke sumur
4. **Peta pressure per cell** — keliatan pressure depletion menyebar dari sumur ke reservoir
5. **Peta saturasi per cell** — keliatan pergerakan fluida di reservoir

---

## 7. Kegunaan Software Simulator di Dunia Nyata

Software ini bukan hanya untuk membuktikan perhitungan benar — ini adalah **alat prediksi** untuk pengambilan keputusan engineering:

- **Prediksi produksi** — berapa oil, water, gas yang akan diproduksi selama 10-30 tahun ke depan
- **Optimasi pengembangan** — penentuan lokasi sumur, jumlah sumur optimal, strategi produksi
- **Estimasi cadangan** — dari recovery factor bisa diestimasikan total oil yang bisa diambil (reserve)
- **Evaluasi EOR** — uji coba injeksi CO2, surfactant, steam di simulator sebelum diimplementasikan di lapangan

Akurasi Newton, akurasi Jacobian, dan akurasi PVT semuanya berpengaruh — karena error kecil di satu timestep bisa terakumulasi menjadi error besar di timestep ke-1000.
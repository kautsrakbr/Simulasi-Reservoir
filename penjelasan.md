# Penjelasan Software CoreReservoir

## Apa Itu CoreReservoir?

**CoreReservoir** adalah software simulasi reservoir minyak dan gas berbasis desktop yang dibangun dengan Python dan antarmuka grafis PySide6 (Qt). Software ini mensimulasikan bagaimana fluida (minyak, air, dan gas) mengalir di dalam formasi batuan bawah tanah seiring waktu, menggunakan metode numerik finite difference dengan solver Newton-Raphson.

Software ini bukan hanya alat hitung sederhana — ia dirancang dengan arsitektur berlapis yang memisahkan fisika, numerik, domain data, dan antarmuka pengguna secara bersih.

---

## Tujuan Utama

1. Memodelkan aliran tiga fasa (minyak, air, gas) dalam grid reservoir 3D.
2. Menyelesaikan persamaan diferensial aliran secara numerik langkah demi langkah (time stepping).
3. Menampilkan hasil simulasi (tekanan, saturasi, residual) secara visual kepada pengguna.
4. Memberikan pengalaman pengguna yang profesional dengan UI modern berbasis tema biru petroleum.

---

## Struktur Lapisan Software

Software ini dibagi menjadi empat lapisan utama yang tidak saling mencampuri:

```
┌────────────────────────────────────────┐
│          ANTARMUKA PENGGUNA            │
│  windows/ + ui/ + assets/style.qss    │
│  (PySide6, Qt Widgets, tema visual)   │
├────────────────────────────────────────┤
│          SERVICE / ORCHESTRATION       │
│  modules/                              │
│  (simulasi service, validasi, worker,  │
│   plot service, report service)        │
├────────────────────────────────────────┤
│          ENGINE SIMULASI               │
│  engine/                               │
│  (fisika, numerik, grid, properties,   │
│   domain data, IO)                     │
└────────────────────────────────────────┘
```

---

## Penjelasan Setiap Folder

### `windows/` — Antarmuka Pengguna
Berisi semua halaman GUI yang ditampilkan ke pengguna:

| File | Fungsi |
|---|---|
| `main_window.py` | Jendela utama, sidebar navigasi, toolbar Run/Stop, dock log |
| `dashboard_page.py` | Ringkasan status proyek dengan kartu berwarna |
| `grid_page.py` | Input dimensi grid reservoir (Nx, Ny, Nz, Dx, Dy, Dz) |
| `pvt_page.py` | Tabel PVT (pressure-volume-temperature) untuk fluida |
| `rock_page.py` | Tabel batuan (relative permeability, capillary pressure) |
| `initial_page.py` | Kondisi awal reservoir (kedalaman, saturasi awal) |
| `model_page.py` | Konfigurasi proyek dan pengaturan solver |
| `run_page.py` | Monitor eksekusi simulasi + live residual chart |
| `results_page.py` | Tampilan hasil: ringkasan, tren, log retry, detail sel |

### `modules/` — Service Layer
Jembatan antara UI dan engine:

| File | Fungsi |
|---|---|
| `simulation_service.py` | Memanggil engine simulasi, meneruskan callback progress |
| `run_worker.py` | Menjalankan simulasi di background thread (QThread) |
| `validation_service.py` | Memvalidasi input proyek sebelum simulasi |
| `project_service.py` | Load/save konfigurasi proyek |
| `results_service.py` | Memproses dan menyajikan hasil simulasi |
| `plot_service.py` | Menghasilkan grafik untuk halaman hasil |
| `report_service.py` | Ekspor laporan |

### `engine/` — Inti Kalkulasi
Semua rumus fisika dan numerik berada di sini:

#### `engine/domain/` — Model Data
Dataclass yang mendefinisikan semua objek data utama:
- `ProjectConfig` — konfigurasi lengkap proyek (grid, PVT, batuan, solver)
- `ReservoirState` — state reservoir saat ini (tekanan P, saturasi Sw, Sg per sel)
- `GridModel` — model grid dengan koneksi antar sel
- `RunResult` — hasil akhir simulasi

#### `engine/grid/` — Grid dan Geometri
- Membangun grid 3D dari spesifikasi (Nx×Ny×Nz)
- Menghitung transmissibility antar sel yang berdekatan
- Mengelola indeks dan koneksi antar sel

#### `engine/physics/` — Fisika Aliran
- **`transmissibility.py`** — permeabilitas transmisi antar sel
- **`flux.py`** — fluks fasa minyak/air/gas antar sel
- **`accumulation.py`** — suku akumulasi (perubahan massa per sel)
- **`residual.py`** — residual = fluks bersih − akumulasi (target: mendekati nol)
- **`potential.py`** — potensial aliran (tekanan + gravitasi)
- **`wells.py`** — model sumur

#### `engine/properties/` — Properti Fluida dan Batuan
- **`pvt.py`** — interpolasi tabel PVT (Bo, Bw, Bg, μo, μw, μg, Rs)
- **`relperm.py`** — interpolasi relative permeability (kro, krw, krg)
- **`capillary.py`** — capillary pressure (Pcow, Pcgw)
- **`densities.py`** — densitas fasa di kondisi reservoir
- **`compressibility.py`** — kompresibilitas batuan dan fluida

#### `engine/numerics/` — Numerik
- **`jacobian_fd.py`** — matriks Jacobian via finite difference
- **`linear_solver.py`** — pemilih solver linear (BiCGStab atau fallback)
- **`bicgstab.py`** — solver BiCGStab iteratif
- **`ilu.py`** — preconditioner ILU(0) untuk mempercepat konvergensi
- **`sparse_matrix.py`** — representasi matriks jarang (CSR)
- **`convergence.py`** — kriteria konvergensi Newton

#### `engine/simulation/` — Eksekusi Simulasi
- **`runner.py`** — loop utama simulasi (time stepping)
- **`newton.py`** — satu iterasi Newton-Raphson
- **`timestep.py`** — kontrol ukuran time step (adaptif)
- **`initializer.py`** — inisialisasi state awal dari kondisi awal
- **`events.py`** — event sistem (misalnya perubahan sumur)

#### `engine/io/` — Input/Output Data
- Pembacaan tabel PVT, batuan, grid dari file
- Load/save konfigurasi proyek

#### `engine/reporting/` — Pelaporan Hasil
- Membangun struktur `RunResult` dari data simulasi
- Ekspor ringkasan dan detail step

---

## Alur Kerja Simulasi (Ringkas)

```
Input Pengguna (Grid, PVT, Rock, Kondisi Awal, Solver)
        │
        ▼
   Validasi Input
        │
        ▼
   Bangun Grid (transmissibility, koneksi)
        │
        ▼
   Inisialisasi State Awal (P₀, Sw₀, Sg₀)
        │
        ▼
   ┌─── Loop Time Step ────────────────────────────────┐
   │                                                   │
   │  ┌── Loop Newton-Raphson ───────────────────┐    │
   │  │  1. Hitung properti (PVT, relperm, dll.) │    │
   │  │  2. Hitung transmissibility terbaru       │    │
   │  │  3. Hitung fluks antar sel                │    │
   │  │  4. Hitung suku akumulasi                 │    │
   │  │  5. Hitung residual R = flux − acc        │    │
   │  │  6. Bangun Jacobian (J = ∂R/∂x)          │    │
   │  │  7. Selesaikan J·Δx = −R (BiCGStab+ILU) │    │
   │  │  8. Update state: P, Sw, Sg += Δx        │    │
   │  │  9. Cek konvergensi → ulangi jika perlu   │    │
   │  └──────────────────────────────────────────┘    │
   │                                                   │
   │  Jika konvergen → accept, lanjut step berikutnya  │
   │  Jika gagal → shrink dt, retry (max 8 kali)       │
   └───────────────────────────────────────────────────┘
        │
        ▼
   Kumpulkan Hasil (tekanan, saturasi, residual per step)
        │
        ▼
   Tampilkan di Halaman Results (grafik, tabel, ekspor)
```

---

## Antarmuka Pengguna (UI)

Tema visual: **Petroleum Blue Enterprise**
- Sidebar navigasi kiri dengan latar `#0F2035` (biru gelap)
- Area konten dengan latar `#EEF2F6` (abu terang)
- Aksen biru utama `#0F5C8E`
- Tombol **▶ Run** dan **■ Stop** di toolbar atas
- **Dashboard** menampilkan status setiap komponen input dengan kartu berwarna (hijau = OK, merah = error, abu = belum diisi)
- **Run Page** menampilkan:
  - Live residual chart (grafik residual vs waktu simulasi)
  - Metrik langkah terkini (step, waktu, Δt, iterasi Newton, residual)
  - Log teks berwarna terminal (`#0B1929` hitam, teks biru)
- **Results Page** dengan tab: Ringkasan | Tren | Retry Log | Detail Sel
- **Dock konsol** di bagian bawah jendela untuk log real-time

---

## Teknologi yang Digunakan

| Teknologi | Peran |
|---|---|
| **Python 3.x** | Bahasa utama |
| **PySide6** | Framework GUI (Qt untuk Python) |
| **Dataclasses** | Model data domain yang bersih |
| **QThread** | Eksekusi simulasi di background (agar UI tidak freeze) |
| **BiCGStab + ILU(0)** | Solver sistem linear jarang |
| **Newton-Raphson** | Solver nonlinear untuk persamaan aliran |
| **Finite Difference** | Diskretisasi persamaan diferensial parsial |

---

## Referensi Teori

Software ini didasarkan pada teori simulasi reservoir standar industri:
- Persamaan kontinuitas tiga fasa (minyak, air, gas)
- Hukum Darcy untuk aliran di media berpori
- Metode finite difference implisit (backward Euler)
- Newton-Raphson untuk persamaan nonlinear
- Transmissibility harmonic mean antar sel

Referensi utama: workbook VBA `ressim_NewClass2.xlsm` dari Mas Zuher, yang menjadi blueprint implementasi rumus-rumus numerik di engine ini.

---

*Dibuat otomatis berdasarkan analisis kode sumber CoreReservoir — 31 Mei 2026*

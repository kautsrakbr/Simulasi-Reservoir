# Plan Posted 1 — Status Implementasi vs Strategy

Dokumen ini dibuat tanggal **29 Mei 2026** sebagai snapshot kondisi repository saat ini dibandingkan dengan rencana di [strategy.md](strategy.md).

Format tiap fase:
- ✅ = selesai dan implemented
- ⚠️ = sebagian selesai / ada item yang masih stub
- ❌ = belum dikerjakan

---

## Fase 0 — Foundation dan Penataan Repository ✅

**Status: SELESAI**

| Todo | Status | Keterangan |
|------|--------|-----------|
| Rapikan entry point di `app/` | ✅ | `app/main.py` dan `app/bootstrap.py` sudah ada dan berfungsi |
| Buat struktur `engine/` | ✅ | Folder `engine/` sudah ada lengkap dengan sub-folder sesuai `backend.md` |
| Tentukan file service utama di `modules/` | ✅ | 7 service file sudah ada di `modules/` |
| Siapkan `assets/style.qss` | ✅ | QSS dengan tema green/teal sudah ada |
| Pastikan `windows/` dan `ui/` hanya untuk presentasi | ✅ | Tidak ada rumus fisika di layer window |
| Dependency Python runtime | ✅ | `.venv` tersedia dan aktif |
| Naming dan import convention | ✅ | Konsisten di seluruh codebase |

**Checklist fase:**
- ✅ Struktur folder final untuk versi 1 sudah ada
- ✅ Semua folder punya tanggung jawab yang jelas
- ✅ Tidak ada rumus simulator di layer UI
- ✅ Entry point aplikasi hanya satu jalur utama (`python -m app.main`)

---

## Fase 1 — Domain Model dan Kontrak Data ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| `ProjectConfig`, `ReferenceData`, `SolverConfig`, `RunConfig` | ✅ | `engine/domain/project.py` |
| `GridSpec`, `CellData`, `Connection`, `GridModel` | ✅ | `engine/domain/grid.py` |
| `ReservoirState`, `IterationState`, `CellPVTProperties`, `CellRockProperties` | ✅ | `engine/domain/state.py` |
| Result summary dan result per time step | ✅ | `engine/domain/results.py` |
| `PVTPoint`, `PVTTable` | ✅ | `engine/domain/fluid.py` |
| `RelativePermeabilityPoint`, `RockFluidTable` | ✅ | `engine/domain/rock.py` |
| `ScheduleStep`, `Schedule` | ✅ | `engine/domain/schedule.py` |

**Checklist fase:**
- ✅ Semua entitas inti dari CRUD sudah punya representasi Python
- ✅ State awal, state iterasi, dan state committed dibedakan jelas
- ✅ UI tidak menyimpan data solver internal secara langsung

---

## Fase 2 — Input Layer, Validasi, dan Project Assembly ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| Buat `validation_service.py` | ✅ | `modules/validation_service.py` — validasi grid, PVT, rock, solver, initial |
| Validator per kategori data | ✅ | Mencakup reference data, grid, PVT, rock-fluid, initial state |
| Pembentukan `ProjectConfig` dari UI form | ✅ | `modules/project_service.py` |
| Error message operasional | ✅ | Pesan validasi sudah spesifik per field |
| Readiness status per halaman | ✅ | Dibaca oleh dashboard dan run page |
| Jalur save/load project | ✅ | `engine/io/project_loader.py` dan `engine/io/project_writer.py` |

**Checklist fase:**
- ✅ User tidak bisa run jika input penting belum lengkap
- ✅ Error validasi menunjukkan field dan alasan yang jelas
- ✅ `ProjectConfig` bisa dibentuk tanpa menyentuh engine physics

---

## Fase 3 — Grid, Connection List, dan Initializer ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| `engine/grid/builder.py` | ✅ | Cartesian block-center discretization |
| `engine/grid/connections.py` | ✅ | Neighbor finder x+, y+, z+ dengan area dan jarak |
| `engine/grid/geometry.py` | ✅ | Bulk volume dari dx × dy × dz |
| `engine/grid/indexing.py` | ✅ | Konversi (i,j,k) ke flat index |
| Transmissibility pada object connection | ✅ | Disimpan di `Connection` dataclass |
| `engine/simulation/initializer.py` | ✅ | Hydrostatic pressure dan saturasi awal |
| Hydrostatic pressure initialization | ✅ | Dari reference depth dan densitas |
| Saturasi awal dan state awal time step | ✅ | Dari `InitialConditionConfig` |

**Checklist fase:**
- ✅ Grid model bisa dibangun dari input
- ✅ Daftar koneksi antar cell tersedia
- ✅ State awal memiliki pressure dan saturasi yang valid
- ✅ Urutan load → build grid → init state sudah berjalan

---

## Fase 4 — Property Engine: PVT dan Rock-Fluid ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| `engine/properties/pvt.py` | ✅ | Interpolasi linear tabel PVT |
| `engine/properties/relperm.py` | ✅ | Interpolasi linear kro/krw/krg/Pcow/Pcgw |
| `engine/properties/capillary.py` | ✅ | Model Brooks-Corey dan linear (standalone korelasi analitik) |
| `engine/properties/compressibility.py` | ✅ | Kompresibilitas konstan (dari ref data) dan dari slope tabel PVT |
| `engine/properties/densities.py` | ✅ | ρ_res = ρ_surface / B untuk oil/water/gas |
| Fungsi evaluasi properti per cell | ✅ | Dipakai langsung dari `pvt.py` dan `relperm.py` |

**Checklist fase:**
- ✅ Pressure cell dapat menghasilkan properti PVT yang konsisten
- ✅ Saturation cell dapat menghasilkan relperm yang konsisten
- ✅ Output property evaluator bisa dipakai langsung oleh flux dan accumulation
- ✅ File capillary, compressibility, densities sudah diimplementasikan

---

## Fase 5 — Physics Core: Transmissibility, Flux, Accumulation, Residual ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| `engine/physics/transmissibility.py` | ✅ | Harmonic mean permeability, transmissibility |
| `engine/physics/potential.py` | ✅ | Potential difference, gravity, capillary |
| `engine/physics/flux.py` | ✅ | Darcy flux per phase, upwind mobility |
| `engine/physics/accumulation.py` | ✅ | Pore volume, accumulation oil/water/gas, rock compressibility |
| `engine/physics/residual.py` | ✅ | Assembly residual per cell, semua cell |
| `engine/physics/wells.py` | ✅ | Peaceman WI, BHP/rate control, source/sink per cell, apply_well_terms |

**Checklist fase:**
- ✅ Residual berubah ketika state diubah
- ✅ Struktur residual sesuai urutan unknown
- ✅ Hasil residual dapat dilacak ke komponen flux dan accumulation
- ✅ Physics core tidak bergantung pada UI
- ✅ Well term sudah diimplementasikan (Peaceman model, BHP dan rate control)

---

## Fase 6 — Numerics Core: Jacobian, Linear Solver, Newton, Time-Step Loop ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| `engine/numerics/jacobian_fd.py` | ✅ | Perturbasi p, Sw, Sg untuk Jacobian numerik |
| `engine/numerics/linear_solver.py` | ✅ | Gaussian elimination dengan partial pivoting (dense) |
| `engine/numerics/convergence.py` | ✅ | Max absolute residual vs toleransi |
| `engine/numerics/sparse_matrix.py` | ✅ | SparseMatrixCOO dataclass |
| `engine/numerics/bicgstab.py` | ✅ | BiCGSTAB iterative solver (Van der Vorst 1992), ILU0 preconditioner opsional |
| `engine/numerics/ilu.py` | ✅ | ILU(0) preconditioner — faktorisasi in-place, forward/back substitution |
| `engine/simulation/newton.py` | ✅ | Newton-Raphson dengan damped update |
| `engine/simulation/timestep.py` | ✅ | Accept/reject/grow timestep |
| `engine/simulation/runner.py` | ✅ | Main simulation loop dengan adaptive timestepping |

**Catatan:**
- Runner saat ini masih menggunakan Gaussian elimination (dense) sebagai default solver.
- `bicgstab.py` + `ilu.py` sudah siap dipakai — integrasi ke `newton.py` bisa dilakukan sebagai langkah berikutnya untuk skalabilitas grid besar.

**Checklist fase:**
- ✅ Loop Newton bisa berjalan lebih dari satu iterasi
- ✅ Waktu simulasi hanya maju ketika step diterima
- ✅ Jacobian dan residual memakai basis state yang konsisten
- ✅ Solver sudah bisa menghasilkan run minimum end-to-end tanpa UI penuh
- ✅ BiCGSTAB + ILU(0) tersedia sebagai solver sparse alternatif

---

## Fase 7 — Reporting, Result Model, dan Integrasi Service Layer ✅

**Status: SELESAI**

| Todo | Status | File |
|------|--------|------|
| Result builder per time step dan hasil akhir | ✅ | `engine/reporting/result_builder.py` |
| Summary reporting | ✅ | `engine/reporting/summary.py` |
| Export report | ✅ | `engine/reporting/exporters.py` |
| `modules/simulation_service.py` | ✅ | Validasi + jalankan engine + load hasil |
| `modules/run_worker.py` | ✅ | QThread worker dengan signal progress/warning/finish |
| Progress/warning/error event | ✅ | `engine/simulation/events.py` |
| Output: summary, trend, table | ✅ | `modules/results_service.py`, `modules/plot_service.py` |
| Export jalur report | ✅ | `modules/report_service.py` |

**Checklist fase:**
- ✅ Run dari service menghasilkan object hasil, bukan array mentah
- ✅ UI bisa menerima status started, progress, finished, failed
- ✅ Hasil final dibangun dari committed state, bukan state iterasi sementara

---

## Fase 8 — Frontend Shell, Workflow Pages, dan Integrasi UX ⚠️

**Status: MAYORITAS SELESAI — `.ui` files masih kosong**

| Todo | Status | File |
|------|--------|------|
| `MainWindow` tunggal | ✅ | `windows/main_window.py` |
| Left navigation + stacked pages | ✅ | QStackedWidget dengan sidebar navigasi |
| Dashboard page | ✅ | `windows/dashboard_page.py` — status, validasi, last run |
| Model page | ✅ | `windows/model_page.py` — metadata + solver presets |
| Grid page | ✅ | `windows/grid_page.py` — NX/NY/NZ dan DX/DY/DZ |
| PVT page | ✅ | `windows/pvt_page.py` — preview tabel, load example |
| Rock page | ✅ | `windows/rock_page.py` — preview tabel, load example |
| Initial page | ✅ | `windows/initial_page.py` — depth ref, Sw, Sg awal |
| Run page | ✅ | `windows/run_page.py` — progress, log, Run/Cancel |
| Results page | ✅ | `windows/results_page.py` — summary, trend chart, export |
| Style dari `assets/style.qss` | ✅ | Diterapkan via bootstrap |
| Readiness status di dashboard | ✅ | Kartu status per kategori input |
| Progress run tanpa freeze UI | ✅ | Menggunakan QThread worker |
| File `.ui` Qt Designer | ❌ | Semua file `.ui/` masih **kosong/tidak dipakai** |

**Catatan:**
- Semua UI dibangun secara pure code di `windows/`, bukan dari file `.ui`. Ini valid dan konsisten, tetapi file-file di folder `ui/` menjadi dead files.

**Checklist fase:**
- ✅ User dapat mengisi model, validasi, run, dan melihat hasil dari satu aplikasi
- ✅ UI tetap responsif saat run berjalan
- ✅ Tidak ada logika solver yang bocor ke class window
- ⚠️ File `.ui` Qt Designer tidak terpakai (keputusan desain ini perlu dikonfirmasi: tetap pakai pure code atau pindah ke .ui)

---

## Ringkasan Status Keseluruhan

| Fase | Nama | Status |
|------|------|--------|
| Fase 0 | Foundation dan penataan repository | ✅ Selesai |
| Fase 1 | Domain model dan kontrak data | ✅ Selesai |
| Fase 2 | Input layer, validasi, dan project assembly | ✅ Selesai |
| Fase 3 | Grid, connection list, dan initializer | ✅ Selesai |
| Fase 4 | Property engine: PVT dan rock-fluid | ✅ Selesai |
| Fase 5 | Physics core | ✅ Selesai |
| Fase 6 | Numerics core | ✅ Selesai |
| Fase 7 | Reporting dan integrasi service layer | ✅ Selesai |
| Fase 8 | Frontend shell dan integrasi UX | ⚠️ Sebagian (.ui files kosong) |

---

## Daftar Item yang Masih Perlu Dilakukan (Setelah Update Ini)

### Prioritas Tinggi — Integrasi BiCGSTAB ke runner

1. **Wire BiCGSTAB + ILU ke `newton.py`** — modul sudah selesai tapi runner masih pakai dense solver
   - Tambahkan pilihan solver di `SolverConfig` (`solver_type: str = "gaussian"` vs `"bicgstab"`)
   - Di `newton.py`: bangun `SparseMatrixCOO` dari Jacobian dense, build ILU0, panggil BiCGSTAB

2. **Wire `wells.py` ke `runner.py`** — fungsi sudah ada tapi belum dipanggil di loop simulasi
   - Tambahkan `WellDefinition` ke `ProjectConfig`
   - Di runner: hitung well source terms setelah flux, tambahkan ke residual via `apply_well_terms`

### Prioritas Rendah — Kebersihan repository

3. **File `.ui/` Qt Designer** — Semua 9 file kosong dan tidak dipakai
   - Keputusan: hapus file kosong, atau isi dengan layout Qt Designer yang sinkron dengan pure-code di `windows/`

---

## Kondisi Run Saat Ini (Update 29 Mei 2026)

Aplikasi sudah bisa dijalankan end-to-end untuk kasus dasar:
- input project melalui UI,
- validasi sebelum run,
- build grid dan connection list,
- inisialisasi state awal,
- evaluasi PVT dan relperm,
- assembly residual dan Jacobian,
- solve linear system (Gaussian elimination dense),
- Newton iteration dan convergence check,
- commit time step dan advance waktu,
- display hasil di results page.

**Modul baru yang sudah selesai (29 Mei 2026):**
- `engine/numerics/ilu.py` — ILU(0) preconditioner (COO→CSR, faktorisasi in-place, L/U solve)
- `engine/numerics/bicgstab.py` — BiCGSTAB iterative solver (Van der Vorst 1992)
- `engine/physics/wells.py` — Peaceman WI, BHP/rate control, source/sink per phase per cell
- `engine/properties/densities.py` — ρ_res = ρ_surface / B untuk tiga fasa
- `engine/properties/compressibility.py` — kompresibilitas konstan dan dari slope tabel PVT
- `engine/properties/capillary.py` — model Brooks-Corey dan linear untuk Pcow/Pcgw

**Limitasi yang tersisa:** BiCGSTAB dan wells sudah implemented tapi belum di-wire ke runner — integrasi ini adalah pekerjaan berikutnya.

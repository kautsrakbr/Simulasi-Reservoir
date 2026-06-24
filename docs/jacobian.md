# Konsep: Jacobian (`B`) Frozen/Lagged dengan Interval yang Bisa Diganti

> Status: **sudah diimplementasi** (lihat §6). Dokumen ini menjelaskan desain akhirnya.

---

## 1. Latar belakang

Solver sebelumnya ([engine/simulation/runner.py](../engine/simulation/runner.py)) selalu menghitung ulang Jacobian (`B`) dari nol via finite-difference **setiap iterasi Newton**, tanpa kecuali — mahal karena tiap assembly butuh `3*cell_count` evaluasi residual tambahan ([engine/numerics/jacobian_fd.py](../engine/numerics/jacobian_fd.py)).

UI di [windows/methods_page.py](../windows/methods_page.py#L22-L43) sudah punya toggle "Newton-Raphson" vs "Quasi-Newton", tersimpan di `ProjectConfig.methods.active_method`, tapi field ini **tidak pernah dibaca** solver — pilihan di UI belum punya efek nyata.

## 2. Keputusan desain

Sengaja **bukan** Broyden's method (rank-1 update tiap iterasi) — itu draf awal dokumen ini, tapi diputuskan terlalu kompleks untuk kebutuhan sekarang. Desain final jauh lebih sederhana: **Jacobian dibekukan (frozen)** — dihitung sekali, lalu dipakai ulang apa adanya (tanpa update formula apa pun) untuk beberapa iterasi berikutnya, sebelum dihitung ulang. Ini dikenal di literatur numerik sebagai **modified Newton method** / **Shamanskii's method** / **lagged Jacobian**.

Satu angka tunggal mengontrol seluruh spektrum perilaku:

```
jacobian_refresh_interval = 1   → Newton-Raphson klasik (refresh tiap iterasi, perilaku awal, tidak berubah)
jacobian_refresh_interval = 2   → hitung, reuse 1x, hitung lagi, reuse 1x, ...
jacobian_refresh_interval = 3   → hitung, reuse 2x, hitung lagi, ...
jacobian_refresh_interval = N   → hitung sekali, reuse (N-1) kali, lalu refresh
jacobian_refresh_interval ≥ max_newton_iterations → hitung sekali di awal timestep, reuse selamanya dalam timestep itu
```

## 3. Lokasi implementasi

**Config** — [engine/domain/project.py](../engine/domain/project.py) `SolverConfig.jacobian_refresh_interval: int = 1`.

**Loop Newton** — [engine/simulation/runner.py](../engine/simulation/runner.py) di `run_timestep`:

```python
last_jacobian: list[list[float]] = []
iterations_since_refresh = 0

for iteration in range(1, max_iterations + 1):
    ...
    needs_fresh_jacobian = (not last_jacobian) or iterations_since_refresh >= jacobian_refresh_interval
    if needs_fresh_jacobian:
        last_jacobian = assemble_jacobian_fd(...)
        iterations_since_refresh = 0
    jacobian = last_jacobian
    iterations_since_refresh += 1
    working_state, correction = newton_step(working_state, residual_vector, jacobian, project_config.solver)
```

Tidak ada update formula (Broyden/BFGS) sama sekali — `B` betul-betul dipakai ulang as-is. `apply_newton_update`, damping, clamping, dan fallback `_apply_pressure_relaxation` di [newton.py](../engine/simulation/newton.py) tidak berubah.

**Cakupan cache**: Jacobian beku **hanya dalam satu timestep** — tiap panggilan `run_timestep` baru mulai dari `last_jacobian = []` (refresh wajib di iterasi pertama). Tidak ada cache lintas-timestep.

**Persistence** — [engine/io/project_loader.py](../engine/io/project_loader.py) & [engine/io/project_writer.py](../engine/io/project_writer.py) sudah baca/tulis field `jacobian_refresh_interval` dari/ke file project JSON.

## 4. Hasil smoke test

Grid 3×3×1, 2 timestep, dibandingkan `jacobian_refresh_interval` = 1 vs 3 vs 100:

| `jacobian_refresh_interval` | Jumlah assembly Jacobian (2 timestep) | Iterasi/timestep | Hasil akhir |
|---|---|---|---|
| 1 (baseline) | 32 | 17, 17 | converged |
| 3 | 12 (↓62%) | 17, 17 | **identik** (diff pressure = 0.000000) |
| 100 (≥ max_iter) | 2 | 17, 17 | **identik**, konvergen |

Untuk kasus uji ini, membekukan Jacobian tidak menambah iterasi maupun mengubah hasil akhir — tapi ini **case-dependent**, bukan garansi umum. Pada kasus yang sangat nonlinear (relperm/PVT tajam, dekat bubble point), jumlah iterasi kemungkinan akan naik seiring `jacobian_refresh_interval` membesar — itu trade-off yang harus dipantau per-kasus, bukan diasumsikan selalu gratis.

## 5. Yang belum dikerjakan (di luar scope saat ini)

- **Wiring `active_method` → `jacobian_refresh_interval`**: saat ini dua field ini independen. Toggle UI "Quasi-Newton" belum otomatis mengubah `jacobian_refresh_interval`. Perlu diputuskan: apakah toggle UI cukup set default interval (misal 3), atau perlu kontrol angka eksplisit di UI (spinbox) seperti yang diminta ("bisa input 1, 2, 3, atau lebih").
- **Kontrol UI numerik**: belum ada widget di [methods_page.py](../windows/methods_page.py) untuk mengubah `jacobian_refresh_interval` langsung — saat ini hanya bisa diset lewat file project JSON atau langsung di kode.
- **Reset adaptif** (refresh dini kalau residual naik) — sempat dibahas sebagai ide terpisah, belum diimplementasi, dan belum dibuktikan perlu.




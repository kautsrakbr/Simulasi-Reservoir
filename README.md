# CERITANYA INI SIMULATOR

Simulator reservoir minyak-air-gas berbasis desktop (PySide6). Aplikasi ini
mensimulasikan aliran 3 fasa pada grid reservoir menggunakan metode numerik
Newton-Raphson / Quasi-Newton, lengkap dengan validasi hasil, visualisasi
heatmap per timestep, dan grafik laju produksi (forecast).

## Cara Tercepat Menjalankan (tanpa install Python)

Tidak perlu install Python atau library apapun. Cukup:

1. Buka folder `exe/SimulasiReservoir/`.
2. Jalankan `SimulasiReservoir.exe` (double-click).

Seluruh isi folder `exe/SimulasiReservoir/` (file `.exe` beserta folder
`_internal/`) harus tetap berada di lokasi yang sama -- jangan memindahkan
hanya file `.exe`-nya saja.

## Menjalankan dari Source Code (untuk development)

Prasyarat: Python 3.11+ dan pip.

```bash
# 1. Buat virtual environment (opsional tapi disarankan)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # macOS/Linux

# 2. Install dependency
pip install -r requirements.txt

# 3. Jalankan aplikasi
python -m app.main
```

## Apa Isinya?

Setelah aplikasi terbuka, buka tab **Guide -> User Guide** di sidebar kiri --
di sana ada penjelasan lengkap tentang setiap modul aplikasi (Configuration,
Setup, Properties, Constraints, Simulation Run, Validation, Forecast) dan
langkah-langkah pemakaiannya, langsung di dalam aplikasi.

Ringkasan singkat:

- **Setup** -- atur ukuran grid reservoir dan kondisi awal (tekanan, saturasi).
- **Properties** -- isi tabel PVT fluida dan properti batuan (relative
  permeability, capillary pressure).
- **Constraints** -- tempatkan sumur produksi/injeksi, cek konektivitas antar
  sel, dan atur metode numerik.
- **Simulation Run** -- jalankan simulasi.
- **Validation** -- cek hasil run: residual, konektivitas grid, Jacobian, dan
  perbandingan metode Newton.
- **Forecast** -- grafik & tabel laju produksi Qo/Qw/Qg terhadap waktu.

## Struktur Proyek

- `app/` -- entry point & bootstrap aplikasi (Qt application, stylesheet).
- `engine/` -- logika numerik inti (grid, PVT, fisika aliran, solver Newton).
- `modules/` -- service layer yang menjembatani `engine/` dengan GUI.
- `windows/` -- seluruh halaman/tampilan PySide6.
- `assets/` -- stylesheet (`style.qss`) dan gambar yang dipakai aplikasi.
- `docs/` -- dokumen referensi & catatan teknis tambahan.
- `exe/` -- hasil build executable siap pakai (lihat di atas).

## Build Ulang File .exe

Jika ingin membangun ulang executable setelah mengubah kode:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "SimulasiReservoir" ^
  --add-data "assets;assets" --distpath "exe" app/main.py
```

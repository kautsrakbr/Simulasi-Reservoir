# Strategy Pengembangan Software Simulasi Reservoir

## 1. Tujuan dokumen ini

Dokumen ini adalah file strategi final sebelum eksekusi pembuatan software dimulai.

Fungsi utamanya bukan untuk menjelaskan teori reservoir lagi, tetapi untuk menjelaskan:

- urutan pembangunan software,
- pembagian fase kerja,
- dependency antar fase,
- daftar pekerjaan yang harus diselesaikan,
- checkpoint validasi tiap fase,
- dan aturan agar implementasi tetap konsisten dengan [workflow.md](workflow.md), [frontend.md](frontend.md), [backend.md](backend.md), dan [crud.md](crud.md).

Kalau nanti coding dimulai, dokumen ini dipakai sebagai panduan eksekusi utama tahap demi tahap.

## 2. Posisi tiap dokumen acuan

Supaya tidak bingung saat implementasi, posisi setiap dokumen harus dibedakan dengan jelas.

- [workflow.md](workflow.md): source of truth untuk urutan fisika, loop solver, dan alur runtime simulasi.
- [vba.md](vba.md): source of truth untuk referensi implementasi workbook VBA.
- [crud.md](crud.md): source of truth untuk lifecycle data, owner module, dan boundary create-read-update-delete.
- [frontend.md](frontend.md): source of truth untuk bentuk produk, layout UI, visual system, dan flow interaksi user.
- [backend.md](backend.md): source of truth untuk struktur folder, kontrak layer, peta rumus ke file, dan file minimal backend.
- [strategy.md](strategy.md): source of truth untuk urutan implementasi project.

Aturan praktisnya:

- jika pertanyaannya "urutan solver harus seperti apa?" buka [workflow.md](workflow.md),
- jika pertanyaannya "rumus ini dulu ada di VBA bagian mana?" buka [vba.md](vba.md),
- jika pertanyaannya "data ini dibuat dan diubah oleh siapa?" buka [crud.md](crud.md),
- jika pertanyaannya "fitur ini muncul di UI sebelah mana?" buka [frontend.md](frontend.md),
- jika pertanyaannya "file Python untuk rumus ini harus diletakkan di mana?" buka [backend.md](backend.md),
- jika pertanyaannya "fase implementasinya sekarang ada di tahap mana?" buka [strategy.md](strategy.md).

## 3. Prinsip pengembangan yang wajib dijaga

Supaya project tidak berantakan saat mulai coding, prinsip di bawah ini harus dianggap sebagai aturan kerja.

### 3.1 Rumus fisika hanya boleh hidup di engine

Rumus PVT, relperm, transmissibility, flux, accumulation, residual, Jacobian, dan Newton update tidak boleh ditulis di layer UI.

Tempatnya harus berada di `engine/`, sesuai peta yang sudah ditetapkan di [backend.md](backend.md).

### 3.2 UI tidak boleh menyimpan logika runtime solver

Folder `windows/` dan `ui/` hanya bertugas menampilkan input, status, hasil, dan interaksi user.

UI boleh memanggil service, tetapi UI tidak boleh:

- menghitung residual,
- menyusun Jacobian,
- mengupdate state Newton,
- atau mengelola state solver internal.

### 3.3 Layer `modules/` adalah application/service layer

Folder `modules/` dipakai sebagai jembatan antara UI dan engine.

Contohnya:

- validasi input,
- memulai run,
- menghubungkan worker thread,
- memanggil engine,
- membentuk payload hasil untuk UI.

### 3.4 Pisahkan data input, runtime state, committed state, dan report

Ini wajib mengikuti [crud.md](crud.md).

Jenis data yang harus dipisahkan:

- data input model,
- data referensi dan table,
- state iterasi Newton,
- state yang sudah di-commit di akhir time step,
- output report untuk user.

Kalau semua dicampur di satu object besar, project akan cepat sulit dirawat.

### 3.5 Implementasi harus mengikuti urutan runtime solver

Urutan implementasi inti harus tetap mengikuti alur utama dari [workflow.md](workflow.md):

1. load input,
2. build grid,
3. build connection list,
4. initialize state,
5. evaluate properties,
6. assemble residual,
7. assemble Jacobian,
8. solve linear system,
9. update unknown,
10. check convergence,
11. commit time step,
12. build results dan report.

### 3.6 Coding dilakukan per slice kecil, bukan sekaligus

Satu sesi kerja sebaiknya fokus pada satu slice kecil yang selesai end-to-end, misalnya:

- hanya membangun `GridSpec` dan `GridModel`,
- hanya membangun interpolasi PVT,
- hanya membangun transmissibility,
- hanya membangun UI shell main window,
- hanya membangun run worker.

Tujuannya supaya konteks kerja tetap sempit dan validasi lebih mudah.

## 4. Target produk versi pertama

Target realistis versi pertama software ini adalah desktop application yang sudah bisa berjalan end-to-end untuk workflow inti reservoir simulator.

Fitur yang harus sudah ada pada versi pertama:

- project input untuk data referensi, grid, PVT, dan rock-fluid,
- validasi input sebelum run,
- build grid dan connection list,
- inisialisasi state awal,
- evaluasi properti PVT dan relperm,
- residual dan Jacobian finite-difference,
- linear solve dan Newton iteration,
- time-step loop dasar,
- hasil summary, trend, map sederhana, dan table,
- report hasil run,
- UI shell yang stabil dan mudah dipakai.

Fitur yang boleh ditunda ke fase lanjutan:

- case comparison,
- well editor yang kaya,
- solver advanced settings yang terlalu detail,
- optimasi performa lanjutan,
- model fisika tambahan di luar kebutuhan inti sekarang.

## 5. Urutan besar pengembangan

Supaya software dibangun dengan urut dan aman, implementasi dibagi menjadi sembilan fase utama.

### 5.1 Fase 0 - Foundation dan penataan repository

Tujuan:

- menyiapkan struktur project nyata sebelum engine dan UI dibangun,
- memastikan nama file, folder, dan entry point tidak membingungkan,
- menyiapkan fondasi supaya fase selanjutnya tidak saling tumpang tindih.

Output fase:

- struktur folder inti siap,
- entry point aplikasi jelas,
- style dasar dan dependensi runtime siap,
- keputusan file yang dipakai/dibuang sudah tegas.

Todo fase:

1. rapikan entry point di `app/` supaya ada satu pintu start aplikasi yang jelas,
2. buat struktur `engine/` sesuai [backend.md](backend.md),
3. tentukan file service utama di `modules/`,
4. siapkan `assets/style.qss` sebagai theme base awal,
5. pastikan `windows/` dan `ui/` dipakai hanya untuk presentasi,
6. siapkan daftar dependency Python yang benar-benar diperlukan,
7. tetapkan naming convention dan import convention sejak awal.

Checklist selesai fase:

- struktur folder final untuk versi 1 sudah ada,
- semua folder punya tanggung jawab yang jelas,
- tidak ada rumus simulator di layer UI,
- entry point aplikasi hanya satu jalur utama.

### 5.2 Fase 1 - Domain model dan kontrak data

Tujuan:

- membangun object inti yang akan dipakai semua layer,
- menerjemahkan [crud.md](crud.md) ke bentuk dataclass dan schema Python,
- memastikan input data, runtime state, dan output hasil tidak tercampur.

Output fase:

- dataclass domain inti tersedia,
- struktur data input dan runtime solver sudah stabil,
- kontrak antar layer mulai terbentuk.

Todo fase:

1. buat `ProjectConfig`, `ReferenceData`, `SolverConfig`, dan `RunConfig`,
2. buat `GridSpec`, `CellData`, `Connection`, dan `GridModel`,
3. buat `ReservoirState`, `IterationState`, `CellPVTProperties`, dan `CellRockProperties`,
4. definisikan object untuk result summary dan result per time step,
5. pisahkan data immutable dari data working state,
6. pastikan penamaan field dekat dengan istilah di [workflow.md](workflow.md) agar mudah dilacak,
7. dokumentasikan mapping dari entitas VBA ke object Python.

Checklist selesai fase:

- semua entitas inti dari CRUD sudah punya representasi Python,
- state awal, state iterasi, dan state committed dibedakan jelas,
- UI belum menyimpan data solver internal secara langsung.

### 5.3 Fase 2 - Input layer, validasi, dan project assembly

Tujuan:

- membuat alur input project yang benar dari sisi software,
- memastikan data mentah user bisa diubah menjadi `ProjectConfig` yang valid,
- memblokir run jika input belum layak.

Output fase:

- service validasi input tersedia,
- project bisa dirakit dari input UI,
- pelaporan error dasar ke user sudah ada.

Todo fase:

1. buat `validation_service.py`,
2. definisikan validator untuk reference data, grid, PVT, rock-fluid, dan initial state,
3. buat mekanisme pembentukan `ProjectConfig` dari UI form,
4. siapkan error message yang operasional, bukan error teknis yang mentah,
5. buat aturan readiness status per halaman input,
6. pastikan hasil validasi bisa dibaca oleh page dashboard dan run page,
7. siapkan jalur save/load project jika struktur data dasar sudah stabil.

Checklist selesai fase:

- user tidak bisa run jika input penting belum lengkap,
- error validasi menunjukkan field dan alasan yang jelas,
- `ProjectConfig` bisa dibentuk tanpa menyentuh engine physics.

### 5.4 Fase 3 - Grid, connection list, dan initializer

Tujuan:

- membangun bagian awal runtime solver sesuai [workflow.md](workflow.md),
- memastikan model sudah bisa berubah dari input mentah menjadi model grid yang siap dihitung.

Output fase:

- grid builder berjalan,
- connection list tersedia,
- state awal bisa diinisialisasi.

Todo fase:

1. buat `engine/grid/builder.py`,
2. buat `engine/grid/connections.py`,
3. implement hitung jumlah cell, volume dasar, dan koneksi cartesian,
4. siapkan lokasi transmissibility pada object connection,
5. buat `engine/simulation/initializer.py`,
6. implement hydrostatic pressure initialization dasar,
7. implement saturasi awal dan state awal time step,
8. siapkan pengecekan sederhana untuk model 1-cell dan 2-cell.

Checklist selesai fase:

- grid model bisa dibangun dari input,
- daftar koneksi antar cell bisa dilihat dan dicek,
- state awal memiliki pressure dan saturasi yang valid,
- urutan load -> build grid -> init state sudah berjalan.

### 5.5 Fase 4 - Property engine: PVT dan rock-fluid

Tujuan:

- menerjemahkan evaluator properti dari VBA ke Python,
- memastikan semua properti fluida dan relperm bisa dihitung dari state saat itu,
- menjaga rumus tetap mudah dicari dan diubah manual nanti.

Output fase:

- interpolasi PVT tersedia,
- evaluator relperm dan capillary tersedia,
- properti per cell bisa dihasilkan dari pressure dan saturation.

Todo fase:

1. buat `engine/properties/pvt.py`,
2. buat `engine/properties/relperm.py`,
3. jika perlu, pecah ke `densities.py`, `compressibility.py`, dan `capillary.py`,
4. implement interpolasi tabel PVT,
5. implement perhitungan `Bo`, `Bw`, `Bg`, viskositas, dan parameter turunan yang dibutuhkan,
6. implement interpolasi `kro`, `krw`, `krg`, `Pcow`, dan `Pcgw`,
7. buat fungsi evaluasi properti per cell,
8. verifikasi hasil terhadap contoh kecil dan referensi workbook.

Checklist selesai fase:

- pressure cell dapat menghasilkan properti PVT yang konsisten,
- saturation cell dapat menghasilkan relperm yang konsisten,
- output property evaluator bisa dipakai langsung oleh flux dan accumulation,
- file rumus mudah ditemukan sesuai peta di [backend.md](backend.md).

### 5.6 Fase 5 - Physics core: transmissibility, flux, accumulation, residual

Tujuan:

- membangun jantung persamaan simulasi,
- memastikan residual tiap phase bisa dihitung secara konsisten dari state iterasi.

Output fase:

- transmissibility tersedia,
- flux antar cell tersedia,
- accumulation tersedia,
- residual per cell dan residual global tersedia.

Todo fase:

1. buat `engine/physics/transmissibility.py`,
2. buat `engine/physics/potential.py` bila dipisah,
3. buat `engine/physics/flux.py`,
4. buat `engine/physics/accumulation.py`,
5. buat `engine/physics/residual.py`,
6. implement harmonic permeability dan transmissibility,
7. implement potential difference dan upwind phase flux,
8. implement pore volume efektif dan accumulation tiap phase,
9. implement residual oil, water, dan gas per cell,
10. implement assembly residual penuh untuk semua cell,
11. buat pengujian kecil berbasis kasus 1-cell dan 2-cell.

Checklist selesai fase:

- residual berubah ketika state diubah,
- struktur residual sesuai urutan unknown yang dipilih,
- hasil residual dapat dilacak ke komponen flux dan accumulation,
- physics core belum bergantung pada UI.

### 5.7 Fase 6 - Numerics core: Jacobian, linear solver, Newton, dan time-step loop

Tujuan:

- membuat solver nonlinear benar-benar bisa berjalan,
- menghubungkan residual, Jacobian, linear solver, dan update state dalam satu alur runtime yang utuh.

Output fase:

- Jacobian finite-difference tersedia,
- linear solver tersedia,
- Newton step tersedia,
- runner time-step dasar tersedia.

Todo fase:

1. buat `engine/numerics/jacobian_fd.py`,
2. buat `engine/numerics/linear_solver.py`,
3. jika perlu, pecah ke `ilu.py`, `bicgstab.py`, dan `convergence.py`,
4. buat `engine/simulation/newton.py`,
5. buat `engine/simulation/timestep.py`,
6. buat `engine/simulation/runner.py`,
7. implement perturbasi `p`, `Sw`, `Sg` untuk Jacobian numerik,
8. implement solve `J delta = -R`,
9. implement update Newton ke state iterasi,
10. implement convergence check residual dan perubahan parameter,
11. implement accept/reject time step,
12. pastikan state committed dipisahkan dari state iterasi,
13. buat run sederhana hingga final time.

Checklist selesai fase:

- loop Newton bisa berjalan lebih dari satu iterasi,
- waktu simulasi hanya maju ketika step diterima,
- Jacobian dan residual memakai basis state yang konsisten,
- solver sudah bisa menghasilkan run minimum end-to-end tanpa UI penuh.

### 5.8 Fase 7 - Reporting, result model, dan integrasi service layer

Tujuan:

- memisahkan hasil solver dari internal solver state,
- membuat hasil run mudah dikonsumsi oleh UI, plotting, dan export.

Output fase:

- result builder tersedia,
- service run dari UI tersedia,
- payload hasil untuk dashboard dan results page tersedia.

Todo fase:

1. buat model hasil per time step dan hasil akhir run,
2. buat `result_builder` atau layer reporting sesuai [backend.md](backend.md),
3. buat `modules/simulation_service.py`,
4. buat `modules/run_worker.py` untuk threading UI,
5. hubungkan engine runner ke service layer,
6. siapkan progress event, warning event, dan error event,
7. siapkan output minimal dalam empat bentuk: summary, trend, map sederhana, dan table,
8. siapkan jalur export report bila output model sudah stabil.

Checklist selesai fase:

- run dari service menghasilkan object hasil, bukan array mentah tanpa struktur,
- UI bisa menerima status started, progress, finished, failed,
- hasil final dibangun dari committed state, bukan state iterasi sementara.

### 5.9 Fase 8 - Frontend shell, workflow pages, dan integrasi UX

Tujuan:

- membuat produk desktop yang benar-benar dapat dipakai,
- menerjemahkan [frontend.md](frontend.md) ke UI nyata tanpa merusak batas layer.

Output fase:

- main window siap pakai,
- halaman input dan hasil tersedia,
- user dapat menjalankan simulasi dari UI dengan status yang jelas.

Todo fase:

1. bangun `MainWindow` tunggal,
2. implement top command bar, left navigation, center workspace, right inspector, dan bottom runtime panel,
3. buat page minimum: Dashboard, Model, Grid, PVT, Rock, Run, Results,
4. terapkan style awal dari `assets/style.qss`,
5. terapkan sistem warna, font, border, density, dan icon sesuai [frontend.md](frontend.md),
6. tampilkan readiness status input di dashboard dan page terkait,
7. tampilkan progress run dan log runtime tanpa membekukan UI,
8. tampilkan hasil dalam summary, trend, map, dan table,
9. pastikan alur UI mengikuti workflow user, bukan struktur folder internal.

Checklist selesai fase:

- user dapat mengisi model, validasi, run, dan melihat hasil dari satu aplikasi,
- UI tetap responsif saat run berjalan,
- tidak ada logika solver yang bocor ke class window,
- feel aplikasi sudah mendekati target enterprise engineering desktop.

## 6. Dependency antar fase

Urutan fase di atas tidak boleh dibalik sembarangan karena ada dependency inti.

Urutan dependency yang aman:

1. Fase 0 harus selesai sebelum struktur implementasi melebar.
2. Fase 1 harus selesai sebelum validasi, grid, dan service mulai stabil.
3. Fase 2 harus selesai sebelum run dari UI boleh dibuka penuh.
4. Fase 3 harus selesai sebelum flux dan residual bisa benar-benar dihitung.
5. Fase 4 harus selesai sebelum accumulation dan residual final masuk akal.
6. Fase 5 harus selesai sebelum Jacobian dan Newton loop penuh dapat diuji.
7. Fase 6 harus selesai sebelum UI results dianggap final.
8. Fase 7 dan Fase 8 bisa berjalan sebagian paralel, tetapi kontrak data hasil harus disepakati dulu.

Aturan praktisnya:

- backend numerics tidak boleh menunggu UI cantik selesai,
- tetapi UI run page tidak boleh dianggap selesai kalau service dan event run belum stabil.

## 7. Strategi implementasi per sprint kecil

Supaya pengerjaan tidak terlalu berat dalam satu konteks, tiap fase besar sebaiknya dipecah lagi menjadi sprint kecil.

Format sprint yang disarankan:

1. pilih satu slice kecil,
2. pastikan dependensinya sudah ada,
3. implement satu file atau satu kelompok file yang sangat berdekatan,
4. lakukan validasi paling sempit yang bisa membuktikan slice itu benar,
5. baru pindah ke slice berikutnya.

Contoh sprint yang aman:

- Sprint A: `ProjectConfig`, `GridSpec`, `ReservoirState`
- Sprint B: `validation_service` dasar
- Sprint C: `build_grid()` dan `build_connections()`
- Sprint D: `initialize_state()`
- Sprint E: interpolasi PVT
- Sprint F: interpolasi relperm
- Sprint G: transmissibility
- Sprint H: flux
- Sprint I: accumulation
- Sprint J: residual global
- Sprint K: Jacobian FD
- Sprint L: linear solver wrapper
- Sprint M: Newton step
- Sprint N: time-step runner
- Sprint O: result builder
- Sprint P: run worker
- Sprint Q: main window shell
- Sprint R: input pages
- Sprint S: results page

Ini lebih aman daripada langsung membangun seluruh engine atau seluruh UI sekaligus.

## 8. Strategi validasi per fase

Validasi harus dilakukan sejak awal, bukan menunggu semua fitur selesai.

### 8.1 Validasi untuk domain dan input

Yang dicek:

- object domain bisa dibuat tanpa ambiguity,
- input wajib tidak hilang,
- validasi bisa mendeteksi data kosong atau tidak masuk akal.

### 8.2 Validasi untuk grid dan initializer

Yang dicek:

- jumlah cell benar,
- neighbor connection benar,
- pressure awal dan saturasi awal berada pada range yang valid.

### 8.3 Validasi untuk property engine

Yang dicek:

- hasil interpolasi tabel masuk akal,
- perubahan pressure mengubah properti PVT,
- perubahan saturation mengubah relperm.

### 8.4 Validasi untuk physics core

Yang dicek:

- transmissibility tidak negatif untuk kasus normal,
- flux berubah sesuai arah potential difference,
- residual berubah sesuai perubahan state.

### 8.5 Validasi untuk numerics core

Yang dicek:

- Jacobian dapat dibentuk tanpa mismatch ukuran,
- solve linear menghasilkan correction dengan ukuran benar,
- Newton loop bisa berhenti karena convergence atau rejection yang jelas.

### 8.6 Validasi untuk results dan UI

Yang dicek:

- hasil run bisa dipetakan ke summary, trend, map, dan table,
- UI tidak freeze saat run berjalan,
- error runtime terlihat jelas di user-facing layer.

## 9. Aturan boundary data selama runtime

Agar tetap konsisten dengan [crud.md](crud.md), boundary data di bawah ini harus dijaga.

### 9.1 Data yang dibuat sekali di awal

Contoh:

- `ReferenceData`
- `GridData`
- `PVTTable`
- `RockFluidTable`
- `ConnectionList`

Aturan:

- jangan diubah-ubah oleh UI saat run sedang berjalan,
- jangan dicampur dengan state iterasi,
- simpan sebagai data model yang stabil.

### 9.2 Data yang berubah tiap iterasi Newton

Contoh:

- `IterationState`
- `CellPVT`
- `CellRockFluid`
- `Residual`
- `Jacobian`
- `RHS`
- `NewtonCorrection`

Aturan:

- data ini hanya boleh hidup di runtime solver,
- jangan langsung diikat ke widget UI,
- jangan dianggap sebagai hasil final.

### 9.3 Data yang di-commit saat time step diterima

Contoh:

- `PreviousState`
- state time step baru
- waktu simulasi yang sudah maju

Aturan:

- commit hanya boleh dilakukan setelah convergence dan acceptance,
- report hanya boleh dibangun dari data yang sudah di-commit.

### 9.4 Data output ke user

Contoh:

- summary hasil,
- trend waktu,
- table hasil,
- map pressure dan saturation.

Aturan:

- bangun di layer hasil/report,
- jangan membocorkan internal matrix solver ke UI utama kecuali untuk log teknis.

## 10. Strategi frontend yang paling aman untuk dieksekusi

Implementasi UI harus mengikuti urutan yang realistis, bukan langsung mengejar tampilan kompleks.

### Tahap UI-1

Bangun dulu:

- `MainWindow`,
- layout utama,
- navigation kiri,
- dashboard,
- page input dasar,
- run panel sederhana.

Tujuan:

- user sudah bisa mengisi data, melihat readiness, dan menekan run.

### Tahap UI-2

Tambahkan:

- results page,
- plot residual atau progress,
- report export,
- project save/load.

Tujuan:

- aplikasi enak dipakai end-to-end.

### Tahap UI-3

Tambahkan bila versi pertama sudah stabil:

- case comparison,
- map yang lebih kaya,
- solver settings yang lebih detail,
- editor well yang lebih matang.

Tujuan:

- aplikasi naik kelas menjadi tool engineering yang lebih lengkap.

## 11. Risiko implementasi yang harus dihindari

Beberapa risiko di bawah ini sangat mungkin terjadi kalau coding dimulai tanpa disiplin.

### 11.1 Mencampur rumus dan widget

Risiko:

- sulit debug,
- sulit ganti rumus,
- sulit test engine tanpa membuka UI.

Pencegahan:

- semua rumus tetap di `engine/`,
- UI hanya memanggil service.

### 11.2 Membangun file terlalu banyak sebelum kontraknya stabil

Risiko:

- nama function berubah terus,
- import silang kacau,
- banyak file kosong tanpa arah.

Pencegahan:

- mulai dari file minimal fase 1 di [backend.md](backend.md),
- tambah file baru hanya saat tanggung jawabnya sudah jelas.

### 11.3 Menguji solver hanya dari UI

Risiko:

- bug numerik sulit dilacak,
- setiap error terlihat seperti bug tampilan.

Pencegahan:

- validasi engine secara terpisah,
- baru hubungkan ke UI setelah output model stabil.

### 11.4 Tidak memisahkan state iterasi dan state committed

Risiko:

- hasil report salah,
- state runtime kacau,
- time-step reject sulit dilakukan.

Pencegahan:

- ikuti boundary data dari [crud.md](crud.md),
- buat titik commit yang sangat jelas di runner.

### 11.5 Terlalu cepat mengejar UI cantik

Risiko:

- fondasi backend belum stabil,
- perubahan engine memaksa ubah UI terus-menerus.

Pencegahan:

- selesaikan kontrak data, service, dan result payload lebih dulu,
- rapikan visual setelah struktur penggunaan stabil.

## 12. Definition of done per milestone

Supaya jelas kapan sebuah tahap dianggap selesai, milestone utama di bawah ini dipakai sebagai patokan.

### Milestone A - Project skeleton siap

Selesai jika:

- struktur folder utama final sudah ada,
- entry point aplikasi jelas,
- style base dan service skeleton awal siap.

### Milestone B - Model data dan validasi siap

Selesai jika:

- seluruh input inti bisa dirakit jadi `ProjectConfig`,
- validasi dasar bekerja,
- readiness status input dapat dibentuk.

### Milestone C - Engine pre-processing siap

Selesai jika:

- grid, koneksi, dan state awal bisa dibangun,
- data awal siap masuk ke loop solver.

### Milestone D - Property dan physics core siap

Selesai jika:

- evaluator PVT dan relperm jalan,
- transmissibility, flux, accumulation, dan residual tersedia.

### Milestone E - Solver core siap

Selesai jika:

- Jacobian, linear solver, Newton, dan time-step loop sudah berjalan,
- run minimum bisa mencapai final time atau berhenti dengan alasan numerik yang jelas.

### Milestone F - Product v1 siap dipakai

Selesai jika:

- user bisa mengisi model, validasi, run, dan melihat hasil dari UI,
- report hasil tersedia,
- aplikasi stabil untuk demo internal atau pengembangan lanjutan.

## 13. Urutan eksekusi paling praktis yang direkomendasikan

Kalau harus dipadatkan menjadi urutan kerja paling praktis, maka implementasi sebaiknya dilakukan seperti ini:

1. rapikan struktur project dan buat skeleton `engine/`,
2. buat domain dataclass dan kontrak data,
3. buat validation service dan project assembly,
4. buat grid builder, connection builder, dan initializer,
5. buat evaluator PVT dan relperm,
6. buat transmissibility, flux, accumulation, dan residual,
7. buat Jacobian FD, linear solver wrapper, Newton step, dan runner,
8. buat result builder dan simulation service,
9. buat run worker,
10. bangun UI shell main window,
11. bangun input pages,
12. hubungkan run flow ke UI,
13. bangun results page,
14. rapikan theme, report, dan usability.

Urutan ini paling aman karena mengikuti dependency teknis, sekaligus menjaga agar setiap tahap tetap bisa diuji.

## 14. Penutup

Kalau [workflow.md](workflow.md) adalah peta cara simulator bekerja, dan [backend.md](backend.md) adalah peta tempat kode harus ditulis, maka [strategy.md](strategy.md) adalah peta urutan pembangunan software-nya.

Dengan strategi ini, pengerjaan software bisa dijalankan secara bertahap tanpa kehilangan arah:

- workflow tetap jadi acuan fisika,
- CRUD tetap jadi acuan lifecycle data,
- backend tetap jadi acuan struktur file dan lokasi rumus,
- frontend tetap jadi acuan bentuk produk dan pengalaman user,
- dan strategy tetap jadi acuan urutan implementasi.

Saat coding dimulai nanti, fase yang paling aman untuk dikerjakan pertama adalah `Fase 0`, lalu lanjut ke `Fase 1`, dan seterusnya tanpa melompati dependency inti.
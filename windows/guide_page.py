from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QFrame,
	QHBoxLayout,
	QLabel,
	QScrollArea,
	QVBoxLayout,
	QWidget,
)


def _section_card(title: str, intro: str | None = None) -> tuple[QFrame, QVBoxLayout]:
	card = QFrame()
	card.setObjectName("resultCard")
	lay = QVBoxLayout(card)
	lay.setContentsMargins(18, 16, 18, 16)
	lay.setSpacing(8)

	title_lbl = QLabel(title)
	title_lbl.setObjectName("resultCardTitle")
	title_lbl.setStyleSheet("font-size: 11pt;")
	lay.addWidget(title_lbl)

	sep = QFrame()
	sep.setFrameShape(QFrame.Shape.HLine)
	sep.setObjectName("resultCardSep")
	lay.addWidget(sep)

	if intro:
		intro_lbl = QLabel(intro)
		intro_lbl.setWordWrap(True)
		intro_lbl.setObjectName("resultRowLabel")
		lay.addWidget(intro_lbl)

	return card, lay


def _module_row(parent_layout: QVBoxLayout, name: str, description: str) -> None:
	row = QVBoxLayout()
	row.setContentsMargins(0, 4, 0, 4)
	row.setSpacing(2)

	name_lbl = QLabel(name)
	name_lbl.setStyleSheet("color: #0F5C8E; font-weight: 700; font-size: 9.3pt;")
	row.addWidget(name_lbl)

	desc_lbl = QLabel(description)
	desc_lbl.setWordWrap(True)
	desc_lbl.setObjectName("resultRowLabel")
	row.addWidget(desc_lbl)

	parent_layout.addLayout(row)


def _step_row(parent_layout: QVBoxLayout, number: int, title: str, description: str) -> None:
	row = QHBoxLayout()
	row.setContentsMargins(0, 6, 0, 6)
	row.setSpacing(12)

	badge = QLabel(str(number))
	badge.setFixedSize(24, 24)
	badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
	badge.setStyleSheet(
		"background: #0F5C8E; color: white; border-radius: 12px; font-weight: 700; font-size: 9pt;"
	)
	row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

	text_col = QVBoxLayout()
	text_col.setContentsMargins(0, 0, 0, 0)
	text_col.setSpacing(2)
	title_lbl = QLabel(title)
	title_lbl.setStyleSheet("color: #1F2937; font-weight: 700; font-size: 9.3pt;")
	desc_lbl = QLabel(description)
	desc_lbl.setWordWrap(True)
	desc_lbl.setObjectName("resultRowLabel")
	text_col.addWidget(title_lbl)
	text_col.addWidget(desc_lbl)
	row.addLayout(text_col, 1)

	parent_layout.addLayout(row)


class GuidePage(QWidget):
	"""Static reference page explaining what the app does, what each sidebar
	module is for, and the basic step-by-step workflow -- aimed at a first-time
	user so they aren't lost in the sidebar."""

	def __init__(self) -> None:
		super().__init__()

		header = QWidget(self)
		header.setObjectName("resultHeader")
		hrow = QHBoxLayout(header)
		hrow.setContentsMargins(20, 14, 20, 14)
		title = QLabel("User Guide", header)
		title.setObjectName("resultTitle")
		hrow.addWidget(title)
		hrow.addStretch(1)

		scroll = QScrollArea(self)
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)

		content = QWidget()
		content_lay = QVBoxLayout(content)
		content_lay.setContentsMargins(20, 20, 20, 20)
		content_lay.setSpacing(16)

		# ── Tentang aplikasi ────────────────────────────────────────────────
		about_card, about_lay = _section_card(
			"Tentang Aplikasi Ini",
			"Aplikasi ini adalah simulator reservoir minyak-air-gas sederhana. "
			"Kamu mengatur grid, properti fluida/batuan, sumur, lalu menjalankan "
			"simulasi numerik (metode Newton/Quasi-Newton) untuk melihat bagaimana "
			"tekanan, saturasi, dan laju produksi berubah seiring waktu.",
		)
		content_lay.addWidget(about_card)

		# ── Modul-modul ──────────────────────────────────────────────────────
		modules_card, modules_lay = _section_card(
			"Modul-Modul Aplikasi",
			"Sidebar di kiri dibagi menjadi beberapa grup. Berikut isi tiap grup:",
		)
		_module_row(modules_lay, "Configuration", "Dashboard (ringkasan proyek), Model (pilihan model fisik), dan Solver (pengaturan solver numerik).")
		_module_row(modules_lay, "Setup", "Grid (ukuran & properti tiap sel reservoir) dan Initial (tekanan & saturasi awal sebelum simulasi berjalan).")
		_module_row(modules_lay, "Properties", "PVT (sifat fluida terhadap tekanan: Bo, Bw, Bg, viskositas) dan Rock Properties (relative permeability & capillary pressure).")
		_module_row(modules_lay, "Constraints", "Connectivity 3D (cek koneksi antar-sel), Well Placement (atur lokasi & laju sumur), Jacobian (uji sensitivitas perturbasi sel), dan Methods (pengaturan metode numerik).")
		_module_row(modules_lay, "Simulation Run", "Jalankan simulasi dan pantau progres/log proses solver di sini.")
		_module_row(modules_lay, "Validation", "Cek hasil run: Summary, Residual Check, Grid Connection, Jacobian, dan Newton Comparison.")
		_module_row(modules_lay, "Forecast", "Grafik dan tabel laju produksi Qo/Qw/Qg terhadap waktu, untuk melihat tren produksi.")
		content_lay.addWidget(modules_card)

		# ── Cara pakai ───────────────────────────────────────────────────────
		steps_card, steps_lay = _section_card(
			"Cara Pakai (Langkah Singkat)",
		)
		_step_row(steps_lay, 1, "Atur Setup", "Tentukan ukuran grid di tab Grid, lalu isi kondisi awal reservoir di tab Initial.")
		_step_row(steps_lay, 2, "Isi Properties", "Masukkan tabel PVT fluida dan properti batuan (relative permeability, capillary pressure).")
		_step_row(steps_lay, 3, "Tambahkan Sumur & Constraint", "Di grup Constraints, tempatkan sumur produksi/injeksi di Well Placement, dan cek pengaturan numerik lain bila perlu.")
		_step_row(steps_lay, 4, "Jalankan Simulasi", "Buka Simulation Run, klik tombol jalankan, dan tunggu hingga proses selesai.")
		_step_row(steps_lay, 5, "Lihat Hasil", "Cek Validation untuk verifikasi numerik, dan Forecast untuk melihat tren laju produksi Qo/Qw/Qg.")
		_step_row(steps_lay, 6, "Simpan Proyek", "Gunakan tombol Save/Save As di toolbar atas agar pengaturan tidak hilang.")
		content_lay.addWidget(steps_card)

		# ── Tips ─────────────────────────────────────────────────────────────
		tips_card, tips_lay = _section_card("Tips Cepat")
		tips_text = QLabel(
			"• Klik kanan pada kotak angka untuk mengubah nilainya langsung.\n"
			"• Tombol \"Simpan\" otomatis aktif begitu ada perubahan yang belum disimpan.\n"
			"• Di tab Heatmap, kamu bisa memilih properti dan skema warna sendiri, "
			"dan di sub-tab \"Per Waktu\" kamu bisa memutar animasi perubahan antar timestep."
		)
		tips_text.setWordWrap(True)
		tips_text.setObjectName("resultRowLabel")
		tips_lay.addWidget(tips_text)
		content_lay.addWidget(tips_card)

		content_lay.addStretch(1)
		scroll.setWidget(content)

		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(header)
		root.addWidget(scroll, 1)

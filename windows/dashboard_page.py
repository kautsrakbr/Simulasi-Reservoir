from __future__ import annotations

from PySide6.QtWidgets import (
	QFrame,
	QHBoxLayout,
	QLabel,
	QScrollArea,
	QSizePolicy,
	QTableWidget,
	QTableWidgetItem,
	QHeaderView,
	QVBoxLayout,
	QWidget,
)
from PySide6.QtGui import QFont, QColor, QBrush

from engine.domain.project import ProjectConfig


class DashboardPage(QWidget):
	def __init__(self) -> None:
		super().__init__()

		# ── Header Bar ──────────────────────────────────────────────────────
		self._header = QWidget(self)
		self._header.setObjectName("dashHeader")
		_header_row = QHBoxLayout(self._header)
		_header_row.setContentsMargins(20, 14, 20, 14)

		self._project_title = QLabel("CERITANYA INI SIMULATOR", self._header)
		self._project_title.setObjectName("dashTitle")

		_header_row.addWidget(self._project_title)
		_header_row.addStretch(1)

		# ── Main Scroll Container ────────────────────────────────────────────
		scroll = QScrollArea(self)
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)

		content = QWidget()
		content.setObjectName("dashContent")
		content_lay = QVBoxLayout(content)
		content_lay.setContentsMargins(20, 20, 20, 20)
		content_lay.setSpacing(20)

		# ── Unified Report Canvas (Flat, clean canvas layout) ─────────────────
		self.canvas = QFrame(content)
		self.canvas.setObjectName("dashCanvasCard")
		canvas_lay = QVBoxLayout(self.canvas)
		canvas_lay.setContentsMargins(24, 24, 24, 24)
		canvas_lay.setSpacing(20)

		# Title
		canvas_title = QLabel("LAPORAN SPESIFIKASI RESERVOIR & STATUS NUMERIK")
		canvas_title.setObjectName("dashCardTitle")
		canvas_lay.addWidget(canvas_title)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("dashCardSep")
		canvas_lay.addWidget(sep)

		# Table 1: Specs & Grid Geometry
		self._lbl_table1 = QLabel("1. SPESIFIKASI KASUS & STRUKTUR GRID")
		self._lbl_table1.setObjectName("dashCardTitle")
		self._lbl_table1.setStyleSheet("color: #0F5C8E; font-weight: 700; font-size: 9.5pt;")
		canvas_lay.addWidget(self._lbl_table1)

		self.table_specs = QTableWidget(5, 2)
		self.table_specs.setHorizontalHeaderLabels(["Parameter Geometri", "Nilai Konfigurasi"])
		self.table_specs.verticalHeader().setVisible(False)
		self.table_specs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table_specs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.table_specs.setFixedHeight(190)
		self.table_specs.setShowGrid(True)
		
		# Initialize items
		specs_keys = ["Nama Proyek", "Nama Kasus (Case)", "Status Penyimpanan", "Dimensi Grid (Nx x Ny x Nz)", "Total Sel Reservoir"]
		for idx, key in enumerate(specs_keys):
			item_key = QTableWidgetItem(key)
			item_key.setFont(self._get_bold_font())
			self.table_specs.setItem(idx, 0, item_key)
			self.table_specs.setItem(idx, 1, QTableWidgetItem("—"))
		canvas_lay.addWidget(self.table_specs)

		# Table 2: Initial Saturations
		self._lbl_table2 = QLabel("2. SATURASI FLUIDA & KONDISI BATAS AWAL")
		self._lbl_table2.setObjectName("dashCardTitle")
		self._lbl_table2.setStyleSheet("color: #0F5C8E; font-weight: 700; font-size: 9.5pt;")
		canvas_lay.addWidget(self._lbl_table2)

		self.table_fluids = QTableWidget(4, 2)
		self.table_fluids.setHorizontalHeaderLabels(["Kondisi Awal Reservoir", "Nilai Parameter"])
		self.table_fluids.verticalHeader().setVisible(False)
		self.table_fluids.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table_fluids.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.table_fluids.setFixedHeight(155)
		self.table_fluids.setShowGrid(True)
		
		fluid_keys = ["Reference Depth (ft)", "Saturasi Air Awal (Sw)", "Saturasi Gas Awal (Sg)", "Saturasi Minyak Awal (So)"]
		for idx, key in enumerate(fluid_keys):
			item_key = QTableWidgetItem(key)
			item_key.setFont(self._get_bold_font())
			self.table_fluids.setItem(idx, 0, item_key)
			self.table_fluids.setItem(idx, 1, QTableWidgetItem("—"))
		canvas_lay.addWidget(self.table_fluids)

		# Table 3: Numerical Validation
		self._lbl_table3 = QLabel("3. KELAYAKAN SIMULASI & INTEGRITAS DATA")
		self._lbl_table3.setObjectName("dashCardTitle")
		self._lbl_table3.setStyleSheet("color: #0F5C8E; font-weight: 700; font-size: 9.5pt;")
		canvas_lay.addWidget(self._lbl_table3)

		self.table_valid = QTableWidget(2, 2)
		self.table_valid.setHorizontalHeaderLabels(["Pemeriksaan Numerik", "Hasil Uji Kelayakan"])
		self.table_valid.verticalHeader().setVisible(False)
		self.table_valid.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.table_valid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.table_valid.setFixedHeight(120)
		self.table_valid.setShowGrid(True)
		
		valid_keys = ["Status Validasi", "Daftar Hambatan (Issues)"]
		for idx, key in enumerate(valid_keys):
			item_key = QTableWidgetItem(key)
			item_key.setFont(self._get_bold_font())
			self.table_valid.setItem(idx, 0, item_key)
			self.table_valid.setItem(idx, 1, QTableWidgetItem("—"))
		canvas_lay.addWidget(self.table_valid)

		content_lay.addWidget(self.canvas)
		scroll.setWidget(content)

		# ── Root Layout ──────────────────────────────────────────────────────
		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(0)
		root.addWidget(self._header)
		root.addWidget(scroll, 1)

	def _get_bold_font(self) -> QFont:
		font = QFont()
		font.setBold(True)
		return font

	def set_project_overview(
		self,
		project_config: ProjectConfig,
		validation_errors: list[str],
		run_result=None,
	) -> None:
		# Header
		self._project_title.setText(project_config.name.upper())

		# Update Table 1: Specs
		self.table_specs.setItem(0, 1, QTableWidgetItem(project_config.name))
		self.table_specs.setItem(1, 1, QTableWidgetItem(project_config.run.case_name))
		
		state_text = "Terdapat Perubahan (Belum Disimpan)" if project_config.is_dirty else "Sudah Disimpan & Up-to-date"
		item_state = QTableWidgetItem(state_text)
		if project_config.is_dirty:
			item_state.setForeground(QBrush(QColor("#A86A15")))
		else:
			item_state.setForeground(QBrush(QColor("#2D6A4F")))
		self.table_specs.setItem(2, 1, item_state)

		gs = project_config.grid_spec
		cells = gs.nx * gs.ny * gs.nz
		self.table_specs.setItem(3, 1, QTableWidgetItem(f"{gs.nx} × {gs.ny} × {gs.nz}"))
		self.table_specs.setItem(4, 1, QTableWidgetItem(f"{cells:,} sel"))

		# Update Table 2: Fluids
		ic = project_config.initial_conditions
		so = max(0.0, 1.0 - ic.initial_sw - ic.initial_sg)
		self.table_fluids.setItem(0, 1, QTableWidgetItem(f"{ic.reference_depth:,.2f} ft"))
		self.table_fluids.setItem(1, 1, QTableWidgetItem(f"{ic.initial_sw:.4f}"))
		self.table_fluids.setItem(2, 1, QTableWidgetItem(f"{ic.initial_sg:.4f}"))
		self.table_fluids.setItem(3, 1, QTableWidgetItem(f"{so:.4f}"))

		# Update Table 3: Validation
		if validation_errors:
			item_status = QTableWidgetItem("Gagal Validasi (Ada Hambatan)")
			item_status.setForeground(QBrush(QColor("#B2413F")))
			item_issues = QTableWidgetItem(" • " + "; ".join(validation_errors))
			item_issues.setForeground(QBrush(QColor("#B2413F")))
		else:
			item_status = QTableWidgetItem("Lolos Validasi (Siap Jalan)")
			item_status.setForeground(QBrush(QColor("#2D6A4F")))
			item_issues = QTableWidgetItem("Semua persyaratan terpenuhi, tidak ada error.")
			item_issues.setForeground(QBrush(QColor("#5B6676")))

		self.table_valid.setItem(0, 1, item_status)
		self.table_valid.setItem(1, 1, item_issues)

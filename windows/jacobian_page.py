from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve, QPointF, QRectF, QVariantAnimation, Signal, QTimer, QPropertyAnimation
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPen, QPolygonF
from PySide6.QtWidgets import (
	QButtonGroup,
	QDoubleSpinBox,
	QFrame,
	QGraphicsDropShadowEffect,
	QGraphicsOpacityEffect,
	QHBoxLayout,
	QLabel,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QSplitter,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import PerturbationConfig, ProjectConfig
from engine.grid.builder import build_grid
from engine.physics.transmissibility import update_grid_transmissibility
from windows.connectivity_3d_page import _Connectivity3DWidget


# ── Helpers ────────────────────────────────────────────────────────────────────

_VAR_META = {
	"P":  ("∂P",  "#0F5C8E", "Pressure"),
	"Sw": ("∂Sw", "#2563A6", "Water Saturation"),
	"Sg": ("∂Sg", "#0F766E", "Gas Saturation"),
}

_DIR_ARROW = {
	"X": "→", "Y": "↑", "Z": "↗",
	"X+": "→", "X-": "←", "Y+": "↑", "Y-": "↓", "Z+": "↗", "Z-": "↙",
}

_SEG_BASE = """
QPushButton {
	background-color: #F7F9FB; color: #5B6676;
	border: 1.5px solid #D7DEE7; padding: 8px 14px;
	font-size: 9pt; font-weight: 700; min-height: 34px;
}
QPushButton:hover  { background-color: #EEF2F6; color: #1F2937; border-color: #B8C3D1; }
QPushButton:checked { background-color: #0F5C8E; color: #ffffff; border-color: #0F5C8E; }
"""


# ── 3D Widget ──────────────────────────────────────────────────────────────────

class _Jacobian3DWidget(_Connectivity3DWidget):
	"""Connectivity viewer repurposed for Jacobian cell selection."""

	_COLORS: dict[str, tuple] = {
		"normal":    ((247, 249, 251), (215, 222, 231)),
		"connected": ((220, 238, 227), ( 45, 106,  79)),
		"well":      ((243, 228, 199), (183, 121,  31)),
		"perturbed": ((220, 234, 247), ( 15,  92, 142)),
	}

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self._well_info: dict[int, tuple[str, str]] = {}  # cell2d → (name, well_type)

	def _draw_legend(self, p) -> None:
		entries = [
			("Normal",    "normal"),
			("Connected", "connected"),
			("Well Cell", "well"),
			("Perturbed", "perturbed"),
		]
		x0, y0 = 12, 12
		p.setFont(QFont("Segoe UI", 8))
		for lbl, mode in entries:
			base_rgb, bdr_rgb = self._COLORS.get(mode, self._COLORS["normal"])
			p.setBrush(QBrush(QColor(*base_rgb)))
			p.setPen(QPen(QColor(*bdr_rgb), 1.5))
			p.drawRoundedRect(QRectF(x0, y0, 14, 14), 3, 3)
			p.setPen(QColor("#5B6676"))
			p.drawText(QRectF(x0 + 18, y0, 80, 14),
					   Qt.AlignmentFlag.AlignVCenter, lbl)
			y0 += 20

	def _draw_overlay(self, p) -> None:
		if not self._well_info:
			return

		scale   = self._last_base_scale
		centres = self._top_face_centres
		plane   = self._nx * self._ny

		pole_h  = max(20, min(50, int(scale * 0.95)))
		head_r  = max(5,  min(14, int(scale * 0.30)))
		pole_w  = max(2.0, min(5.0, scale * 0.09))
		flag_h  = max(14, min(28, int(scale * 0.55)))
		lbl_sz  = max(6,  min(10, int(scale * 0.37)))

		lbl_font = QFont("Segoe UI Variable Text", lbl_sz)
		lbl_font.setBold(True)

		for cell2d_val, (name, well_type) in self._well_info.items():
			centre = None
			for _iz in range(self._nz - 1, -1, -1):
				centre = centres.get(_iz * plane + cell2d_val)
				if centre is not None:
					break
			if centre is None:
				continue
			if well_type == "production":
				dark_col  = QColor("#6B4710")
				main_col  = QColor("#B7791F")
				light_col = QColor("#D9A14A")
				glow_col  = QColor(217, 161, 74, 80)
			else:
				dark_col  = QColor("#1B4566")
				main_col  = QColor("#2563A6")
				light_col = QColor("#5B8FC4")
				glow_col  = QColor(91, 143, 196, 80)

			x, y   = centre.x(), centre.y()
			top_y  = y - pole_h
			tip_pt = QPointF(x, top_y)

			# Ground shadow
			p.setBrush(QBrush(QColor(0, 0, 0, 35)))
			p.setPen(Qt.PenStyle.NoPen)
			p.drawEllipse(QPointF(x, y + 1.5), head_r * 0.9, head_r * 0.26)

			# Glow ring
			p.setBrush(QBrush(glow_col))
			p.setPen(Qt.PenStyle.NoPen)
			p.drawEllipse(QPointF(x, y), head_r * 1.4, head_r * 0.42)

			# Gradient pole
			pole_grad = QLinearGradient(x - pole_w, top_y, x + pole_w, y)
			pole_grad.setColorAt(0.0, light_col)
			pole_grad.setColorAt(1.0, dark_col)
			p.setBrush(QBrush(pole_grad))
			p.setPen(Qt.PenStyle.NoPen)
			p.drawRoundedRect(
				QRectF(x - pole_w / 2, top_y + head_r, pole_w, pole_h - head_r),
				pole_w / 2, pole_w / 2,
			)

			# Pin head
			p.setBrush(QBrush(main_col))
			p.setPen(QPen(QColor("#ffffff"), max(1.2, pole_w * 0.50)))
			p.drawEllipse(tip_pt, head_r, head_r)

			# Specular
			p.setBrush(QBrush(QColor(255, 255, 255, 150)))
			p.setPen(Qt.PenStyle.NoPen)
			spec_r = max(1, head_r // 3)
			p.drawEllipse(
				QPointF(x - head_r * 0.28, top_y - head_r * 0.28),
				spec_r, spec_r,
			)

			# Type letter
			icon_sz = max(4, head_r // 2)
			icon_f  = QFont("Segoe UI", icon_sz)
			icon_f.setBold(True)
			p.setFont(icon_f)
			p.setPen(QColor("#ffffff"))
			p.drawText(
				QRectF(x - head_r, top_y - head_r, head_r * 2, head_r * 2),
				Qt.AlignmentFlag.AlignCenter,
				"P" if well_type == "production" else "I",
			)

			# Flag badge
			p.setFont(lbl_font)
			fm   = p.fontMetrics()
			tw   = fm.horizontalAdvance(name)
			bw   = max(tw + 14, int(flag_h * 2.0))
			bh   = flag_h
			bx   = x + head_r * 0.70
			by   = top_y - bh / 2

			# Badge shadow
			p.setBrush(QBrush(QColor(0, 0, 0, 25)))
			p.setPen(Qt.PenStyle.NoPen)
			p.drawRoundedRect(QRectF(bx + 2, by + 2, bw, bh), 5, 5)

			# Badge gradient
			badge_grad = QLinearGradient(bx, by, bx, by + bh)
			badge_grad.setColorAt(0.0, light_col)
			badge_grad.setColorAt(1.0, dark_col)
			p.setBrush(QBrush(badge_grad))
			p.setPen(QPen(QColor("#ffffff"), 1.0))
			p.drawRoundedRect(QRectF(bx, by, bw, bh), 5, 5)

			p.setPen(QColor("#ffffff"))
			p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, name)

			# Connector notch
			notch_x  = bx
			notch_cy = by + bh / 2
			notch_sz = max(3, bh // 4)
			notch_pts = [
				QPointF(notch_x, notch_cy),
				QPointF(notch_x + notch_sz, notch_cy - notch_sz * 0.6),
				QPointF(notch_x + notch_sz, notch_cy + notch_sz * 0.6),
			]
			p.setBrush(QBrush(light_col))
			p.setPen(Qt.PenStyle.NoPen)
			p.drawPolygon(QPolygonF(notch_pts))


# ── Main Page ──────────────────────────────────────────────────────────────────

class JacobianPage(QWidget):
	perturbationChanged = Signal(object)

	def __init__(self) -> None:
		super().__init__()
		self.project_config: ProjectConfig | None = None
		self._perturbed_cell: int | None = None
		self._connections: list = []
		self._table_collapsed = False
		self._saved_table_width = 400
		self._row_modes: dict[str, str] = {"P": "pct", "Sw": "pct", "Sg": "pct"}
		self._row_toggles: dict[str, tuple[QPushButton, QPushButton]] = {}
		self._spins: dict = {}         # var → (QDoubleSpinBox, auto_lbl)
		self._auto_eps: dict = {}

		root = QVBoxLayout(self)
		root.setSpacing(0)
		root.setContentsMargins(0, 0, 0, 0)

		# ── Splitter ────────────────────────────────────────────────────────
		self.splitter = QSplitter(Qt.Orientation.Horizontal)
		self.splitter.setStyleSheet(
			"QSplitter::handle { background-color: #D7DEE7; width: 1px; }"
		)

		# ── Left panel ──────────────────────────────────────────────────────
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		left_layout.setContentsMargins(0, 0, 0, 0)
		left_layout.setSpacing(0)

		toolbar = QWidget()
		toolbar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #D7DEE7;")
		tbar = QHBoxLayout(toolbar)
		tbar.setContentsMargins(16, 8, 16, 8)
		tbar.setSpacing(14)

		title_lbl = QLabel("Jacobian Inspector")
		title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #0F5C8E;")
		tbar.addWidget(title_lbl)
		tbar.addStretch(1)

		self._jac_status = QLabel("Grid belum dikonfigurasi.")
		self._jac_status.setStyleSheet("""
			background-color: #DCEAF7; color: #0F5C8E;
			border: 1px solid #A9CCE5; border-radius: 8px;
			padding: 6px 14px; font-size: 9pt; font-weight: 600;
		""")
		self._jac_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		tbar.addWidget(self._jac_status)

		# Focus mode button
		self.btn_focus = QPushButton("Focus Mode")
		self.btn_focus.setCheckable(True)
		self.btn_focus.setChecked(False)
		self.btn_focus.setCursor(Qt.CursorShape.PointingHandCursor)
		self.btn_focus.setStyleSheet("""
			QPushButton {
				background-color: #ffffff;
				color: #5B6676;
				border: 1.5px solid #D7DEE7;
				border-radius: 8px;
				padding: 6px 14px;
				font-size: 9pt;
				font-weight: 700;
			}
			QPushButton:hover {
				background-color: #DCEAF7;
				border-color: #A9CCE5;
				color: #0F5C8E;
			}
			QPushButton:checked {
				background-color: #0F5C8E;
				border-color: #0F5C8E;
				color: #ffffff;
				font-weight: 700;
			}
		""")
		self.btn_focus.clicked.connect(self._on_focus_toggle)
		tbar.addWidget(self.btn_focus)

		btn_reset = QPushButton("↺  Reset View")
		btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_reset.setStyleSheet("""
			QPushButton { background-color:#ffffff; color:#5B6676; border:1.5px solid #D7DEE7;
				border-radius:8px; padding:6px 14px; font-size:9pt; font-weight:700; }
			QPushButton:hover { background-color:#DCEAF7; border-color:#A9CCE5; color:#0F5C8E; }
		""")
		btn_reset.clicked.connect(lambda: self._jac3d.reset_view())
		tbar.addWidget(btn_reset)

		self.btn_toggle = QPushButton("▶")
		self.btn_toggle.setFixedSize(34, 34)
		self.btn_toggle.setToolTip("Hide Details")
		self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
		self.btn_toggle.setStyleSheet("""
			QPushButton { background-color:#ffffff; color:#5B6676; border:1.5px solid #D7DEE7;
				border-radius:8px; font-size:11pt; font-weight:bold; padding:0px; }
			QPushButton:hover { background-color:#DCEAF7; border-color:#A9CCE5; color:#0F5C8E; }
		""")
		self.btn_toggle.clicked.connect(self._toggle_panel)
		tbar.addWidget(self.btn_toggle)

		left_layout.addWidget(toolbar)

		left_content = QWidget()
		lc_layout = QVBoxLayout(left_content)
		lc_layout.setContentsMargins(12, 12, 6, 12)
		lc_layout.setSpacing(0)

		self._jac3d = _Jacobian3DWidget()
		self._jac3d.cell_clicked.connect(self._on_cell_clicked)
		lc_layout.addWidget(self._jac3d, 1)
		left_layout.addWidget(left_content, 1)

		# ── Right panel ─────────────────────────────────────────────────────
		self.right_panel = QWidget()
		self.right_panel.setObjectName("rightPanel")
		self.right_panel.setStyleSheet("QWidget#rightPanel { background-color: #F7F9FB; }")
		right_layout = QVBoxLayout(self.right_panel)
		right_layout.setContentsMargins(0, 0, 0, 0)
		right_layout.setSpacing(0)

		right_header = QWidget()
		right_header.setObjectName("rightHeader")
		right_header.setStyleSheet(
			"QWidget#rightHeader { background-color: #ffffff; border-bottom: 1px solid #D7DEE7; }"
		)
		rh = QHBoxLayout(right_header)
		rh.setContentsMargins(16, 8, 16, 8)
		hdr_lbl = QLabel("Jacobian Non-Zero Entries")
		hdr_lbl.setStyleSheet(
			"font-size: 11pt; font-weight: 700; color: #1F2937; letter-spacing: 0.5px;"
		)
		rh.addWidget(hdr_lbl)
		rh.addStretch(1)
		right_layout.addWidget(right_header)

		# ── Selected cell info banner ───────────────────────────────────────────────
		self._cell_info_banner = QWidget()
		self._cell_info_banner.setObjectName("cellInfoBanner")
		self._cell_info_banner.setStyleSheet("""
			QWidget#cellInfoBanner {
				background-color: #ffffff;
				border-bottom: 1px solid #D7DEE7;
			}
		""")
		ci_outer = QHBoxLayout(self._cell_info_banner)
		ci_outer.setContentsMargins(16, 10, 16, 10)
		ci_outer.setSpacing(0)

		# Left: cell number block
		ci_num_block = QWidget()
		ci_num_block.setStyleSheet("background: transparent;")
		ci_num_lay = QVBoxLayout(ci_num_block)
		ci_num_lay.setContentsMargins(0, 0, 0, 0)
		ci_num_lay.setSpacing(0)
		self._ci_tag = QLabel("PERTURB CELL")
		self._ci_tag.setStyleSheet(
			"font-size: 6pt; font-weight: 700; color: #93A1B2; letter-spacing: 1.8px; background: transparent;"
		)
		ci_num_lay.addWidget(self._ci_tag)
		self._ci_cell_num = QLabel("Cell -")
		self._ci_cell_num.setStyleSheet(
			"font-size: 17pt; font-weight: 700; color: #1F2937; background: transparent;"
		)
		ci_num_lay.addWidget(self._ci_cell_num)
		ci_outer.addWidget(ci_num_block)

		# Divider
		ci_div = QFrame()
		ci_div.setFrameShape(QFrame.Shape.VLine)
		ci_div.setStyleSheet("background: #D7DEE7; border: none; max-width: 1px; margin: 4px 16px;")
		ci_outer.addWidget(ci_div)

		# Right: info grid
		ci_info = QWidget()
		ci_info.setStyleSheet("background: transparent;")
		ci_info_lay = QVBoxLayout(ci_info)
		ci_info_lay.setContentsMargins(0, 0, 0, 0)
		ci_info_lay.setSpacing(4)

		self._ci_conn_lbl = QLabel("-")
		self._ci_conn_lbl.setStyleSheet(
			"font-size: 8pt; color: #93A1B2; background: transparent;"
		)
		ci_info_lay.addWidget(self._ci_conn_lbl)

		self._ci_well_lbl = QLabel("")
		self._ci_well_lbl.setStyleSheet(
			"font-size: 8pt; color: #A86A15; font-weight: 700; background: transparent;"
		)
		ci_info_lay.addWidget(self._ci_well_lbl)
		ci_outer.addWidget(ci_info, 1)

		self._cell_info_banner.hide()
		right_layout.addWidget(self._cell_info_banner)

		right_content = QWidget()
		rc_layout = QVBoxLayout(right_content)
		rc_layout.setContentsMargins(12, 12, 12, 0)
		rc_layout.setSpacing(10)

		self.scroll_area = QScrollArea()
		self.scroll_area.setWidgetResizable(True)
		self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
		self.scroll_area.setStyleSheet("background-color: transparent;")

		self.scroll_content = QWidget()
		self.scroll_content.setStyleSheet("background-color: transparent;")
		self.scroll_layout = QVBoxLayout(self.scroll_content)
		self.scroll_layout.setContentsMargins(8, 8, 8, 8)
		self.scroll_layout.setSpacing(8)
		self.scroll_layout.addStretch(1)

		self.scroll_area.setWidget(self.scroll_content)
		rc_layout.addWidget(self.scroll_area, stretch=1)
		right_layout.addWidget(right_content, stretch=1)

		# ── Bottom controls ──────────────────────────────────────────────────────────
		bottom = QWidget()
		bottom.setObjectName("bottomPanel")
		bottom.setMinimumHeight(286)
		bottom.setStyleSheet("""
			QWidget#bottomPanel {
				background-color: #ffffff;
				border-top: 1px solid #D7DEE7;
				border-top-left-radius: 14px;
				border-top-right-radius: 14px;
			}
		""")
		bottom_shadow = QGraphicsDropShadowEffect(bottom)
		bottom_shadow.setBlurRadius(24)
		bottom_shadow.setColor(QColor(15, 23, 42, 35))
		bottom_shadow.setOffset(0, -3)
		bottom.setGraphicsEffect(bottom_shadow)

		bot_layout = QVBoxLayout(bottom)
		bot_layout.setContentsMargins(16, 12, 16, 12)
		bot_layout.setSpacing(7)

		# Section header
		eps_sec_lbl = QLabel("PERTURBATION (ε)")
		eps_sec_lbl.setStyleSheet(
			"font-size: 7.5pt; font-weight: 700; color: #5B6676; letter-spacing: 1.2px;"
		)
		bot_layout.addWidget(eps_sec_lbl)

		# Hint
		hint_lbl = QLabel(
			"Klik sel di grid 3D untuk memilih titik perturbasi.  "
			"Ketiga variabel (P, Sw, Sg) diperturb serentak pada sel yang sama."
		)
		hint_lbl.setWordWrap(True)
		hint_lbl.setStyleSheet("font-size: 7.5pt; color: #93A1B2; font-style: italic;")
		bot_layout.addWidget(hint_lbl)

		# Separator
		_sep = QFrame()
		_sep.setFrameShape(QFrame.Shape.HLine)
		_sep.setStyleSheet("background-color: #D7DEE7; border: none; max-height: 1px; margin: 2px 0;")
		bot_layout.addWidget(_sep)

		# Variable rows styled customly for each variable
		_VAR_DEFS = [
			("P",  "Pressure", "#0F5C8E", "#DCEAF7", "#A9CCE5", "#CFE3F4"),
			("Sw", "Water",    "#2563A6", "#DCE8F2", "#A8C2DA", "#CFE0EC"),
			("Sg", "Gas",      "#0F766E", "#D9EDE9", "#A0CFC7", "#CCE6E1"),
		]
		for _vk, _vname, _vcol, _vbg, _vborder, _vhover in _VAR_DEFS:
			_row_w = QWidget()
			_row_w.setStyleSheet("background: transparent;")
			_row_lay = QHBoxLayout(_row_w)
			_row_lay.setContentsMargins(0, 2, 0, 2)
			_row_lay.setSpacing(8)

			_badge = QLabel(_vk)
			_badge.setFixedSize(28, 22)
			_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
			_badge.setStyleSheet(
				f"background:{_vbg}; color:{_vcol}; border:1.5px solid {_vcol};"
				"border-radius:4px; font-size:8pt; font-weight:800;"
			)
			_row_lay.addWidget(_badge)

			_name_lbl = QLabel(_vname + ":")
			_name_lbl.setFixedWidth(66)
			_name_lbl.setStyleSheet("font-size: 8.5pt; color: #1F2937; font-weight: 600;")
			_row_lay.addWidget(_name_lbl)

			_spn = QDoubleSpinBox()
			_spn.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
			_spn.setRange(0.0001, 100.0)
			_spn.setDecimals(4)
			_spn.setValue(1.0)
			_spn.setFixedWidth(95)
			_spn.setStyleSheet(f"""
				QDoubleSpinBox {{
					border: 1px solid {_vborder};
					border-radius: 6px;
					padding: 3px 5px;
					font-size: 8.5pt;
					background: #ffffff;
					color: #1F2937;
				}}
				QDoubleSpinBox:focus {{
					border-color: {_vcol};
				}}
			""")
			_spn.valueChanged.connect(lambda: self._on_input_changed())
			_row_lay.addWidget(_spn)

			# Segmented control for variable mode (rounded pill, tinted to the variable's color)
			_toggle_w = QWidget()
			_toggle_w.setObjectName("toggleSeg")
			_toggle_w.setStyleSheet(
				f"QWidget#toggleSeg {{ background-color: {_vbg}; border-radius: 8px; }}"
			)
			_toggle_lay = QHBoxLayout(_toggle_w)
			_toggle_lay.setContentsMargins(2, 2, 2, 2)
			_toggle_lay.setSpacing(1)

			_btn_pct = QPushButton("%")
			_btn_abs = QPushButton("psia" if _vk == "P" else "frac")
			_btn_pct.setCheckable(True)
			_btn_abs.setCheckable(True)
			_btn_pct.setFixedWidth(26)
			_btn_abs.setFixedWidth(38)
			_btn_pct.setCursor(Qt.CursorShape.PointingHandCursor)
			_btn_abs.setCursor(Qt.CursorShape.PointingHandCursor)

			_TOGGLE_STYLE = f"""
				QPushButton {{
					font-size: 7.5pt;
					font-weight: 700;
					padding: 2px 0px;
					border: none;
					border-radius: 6px;
					background: transparent;
					color: {_vcol};
					min-height: 20px;
					max-height: 20px;
				}}
				QPushButton:hover {{
					background: #ffffff;
				}}
				QPushButton:checked {{
					background: {_vcol};
					color: #ffffff;
				}}
			"""
			_btn_pct.setStyleSheet(_TOGGLE_STYLE)
			_btn_abs.setStyleSheet(_TOGGLE_STYLE)

			_grp = QButtonGroup(_row_w)
			_grp.addButton(_btn_pct)
			_grp.addButton(_btn_abs)
			_grp.setExclusive(True)
			_btn_pct.setChecked(True)

			_btn_pct.clicked.connect(lambda _, v=_vk: self._set_row_mode(v, "pct"))
			_btn_abs.clicked.connect(lambda _, v=_vk: self._set_row_mode(v, "abs"))

			_toggle_lay.addWidget(_btn_pct)
			_toggle_lay.addWidget(_btn_abs)
			_row_lay.addWidget(_toggle_w)
			self._row_toggles[_vk] = (_btn_pct, _btn_abs)

			_auto_lbl = QLabel("Auto: 1.00%")
			_auto_lbl.setStyleSheet("font-size: 7.5pt; color: #93A1B2; font-style: italic;")
			_row_lay.addWidget(_auto_lbl)

			_btn_rst = QPushButton("Auto")
			_btn_rst.setFixedHeight(22)
			_btn_rst.setToolTip("Reset ke nilai auto")
			_btn_rst.setCursor(Qt.CursorShape.PointingHandCursor)
			_btn_rst.setStyleSheet(f"""
				QPushButton {{
					background: {_vbg};
					color: {_vcol};
					font-size: 7.5pt;
					font-weight: 700;
					border: 1px solid {_vborder};
					border-radius: 4px;
					padding: 0px 8px;
				}}
				QPushButton:hover {{
					background: {_vhover};
					border-color: {_vcol};
				}}
			""")
			_btn_rst.clicked.connect(lambda _, v=_vk: self._reset_to_auto(v))
			_row_lay.addWidget(_btn_rst)
			_row_lay.addStretch(1)

			bot_layout.addWidget(_row_w)
			self._spins[_vk] = (_spn, _auto_lbl)

		# ── Saved delta preview card ──────────────────────────────────────────
		self._preview_card = QWidget()
		self._preview_card.setObjectName("previewCard")
		self._preview_card.setStyleSheet("""
			QWidget#previewCard {
				background-color: #F7F9FB;
				border: 1.5px solid #D7DEE7;
				border-radius: 8px;
			}
		""")
		preview_lay = QVBoxLayout(self._preview_card)
		preview_lay.setContentsMargins(12, 10, 12, 10)
		preview_lay.setSpacing(4)

		preview_title = QLabel("DELTA YANG TERSIMPAN (UNTUK SIMULASI):")
		preview_title.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #5B6676; letter-spacing: 0.8px;")
		preview_lay.addWidget(preview_title)

		self._preview_P = QLabel("-")
		self._preview_P.setStyleSheet("font-size: 8.5pt; font-family: monospace; color: #0F5C8E; font-weight: bold;")
		preview_lay.addWidget(self._preview_P)

		self._preview_Sw = QLabel("-")
		self._preview_Sw.setStyleSheet("font-size: 8.5pt; font-family: monospace; color: #2563A6; font-weight: bold;")
		preview_lay.addWidget(self._preview_Sw)

		self._preview_Sg = QLabel("-")
		self._preview_Sg.setStyleSheet("font-size: 8.5pt; font-family: monospace; color: #0F766E; font-weight: bold;")
		preview_lay.addWidget(self._preview_Sg)

		bot_layout.addWidget(self._preview_card)

		save_row = QHBoxLayout()
		save_row.setContentsMargins(0, 6, 0, 0)
		save_row.setSpacing(10)
		self._saved_status_chip = QLabel("")
		self._saved_status_chip.setObjectName("pageStatusChip")
		save_row.addWidget(self._saved_status_chip)
		save_row.addStretch(1)
		self._save_btn = QPushButton("Simpan Jacobian")
		self._save_btn.setObjectName("constraintSaveButton")
		self._save_btn.setMinimumSize(132, 40)
		self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
		self._save_btn.setEnabled(False)
		self._save_btn.setToolTip("Pilih sel di grid 3D untuk diperturb sebelum menyimpan.")
		self._save_btn.clicked.connect(self._on_save)
		save_row.addWidget(self._save_btn)
		bot_layout.addLayout(save_row)

		right_layout.addWidget(bottom)

		self.splitter.addWidget(left_panel)
		self.splitter.addWidget(self.right_panel)
		self.splitter.setStretchFactor(0, 3)
		self.splitter.setStretchFactor(1, 2)
		self.splitter.setSizes([600, 400])

		root.addWidget(self.splitter, stretch=1)

	# ── Public API ─────────────────────────────────────────────────────────────

	def set_project(self, project_config: ProjectConfig) -> None:
		self.project_config = project_config
		gs = project_config.grid_spec
		self._jac3d._nx = gs.nx
		self._jac3d._ny = gs.ny
		self._jac3d._nz = getattr(gs, "nz", 1)

		try:
			grid_model = build_grid(project_config)
			update_grid_transmissibility(grid_model)
			self._connections = grid_model.connections
		except Exception:
			self._connections = []

		self._jac3d._well_info = {
			w.cell_id: (w.name, w.well_type)
			for w in project_config.wells
		}
		self._perturbed_cell = None

		# Compute auto eps from initial conditions (now 1.00% of reference)
		ic = project_config.initial_conditions
		rd = project_config.reference_data
		self._auto_eps = {
			"P":  rd.reference_pressure * 0.01 if rd.reference_pressure > 0 else 0.01,
			"Sw": ic.initial_sw * 0.01 if ic.initial_sw > 0 else 0.0001,
			"Sg": ic.initial_sg * 0.01 if ic.initial_sg > 0 else 0.0001,
		}

		# Restore saved perturbation config and row modes
		pert = project_config.perturbation
		_deltas = {"P": pert.delta_P, "Sw": pert.delta_Sw, "Sg": pert.delta_Sg}
		
		# Default all rows to pct mode initially
		self._row_modes = {"P": "pct", "Sw": "pct", "Sg": "pct"}

		for var_key, (spn, auto_lbl) in self._spins.items():
			delta = _deltas[var_key]
			
			spn.blockSignals(True)
			if delta > 0.0:
				# If delta exactly matches 1% auto value, keep pct mode (1.0%)
				if abs(delta - self._auto_eps[var_key]) < 1e-9:
					self._row_modes[var_key] = "pct"
					spn.setRange(0.0001, 100.0)
					spn.setValue(1.0)
				else:
					self._row_modes[var_key] = "abs"
					spn.setRange(0.0001, 99999.0)
					spn.setValue(delta)
			else:
				self._row_modes[var_key] = "pct"
				spn.setRange(0.0001, 100.0)
				spn.setValue(1.0)
			spn.blockSignals(False)

			# Sync buttons and auto text
			btn_pct, btn_abs = self._row_toggles[var_key]
			btn_pct.blockSignals(True)
			btn_abs.blockSignals(True)
			if self._row_modes[var_key] == "pct":
				btn_pct.setChecked(True)
				btn_abs.setChecked(False)
				auto_lbl.setText("Auto: 1.00%")
			else:
				btn_pct.setChecked(False)
				btn_abs.setChecked(True)
				v = self._auto_eps[var_key]
				if var_key == "P":
					auto_lbl.setText(f"Auto: {v:.2f} psia")
				else:
					auto_lbl.setText(f"Auto: {v:.5f}")
			btn_pct.blockSignals(False)
			btn_abs.blockSignals(False)

		if pert.perturbed_cell_id > 0:
			self._perturbed_cell = pert.perturbed_cell_id
			
		self._update_saved_deltas_display_from_config(pert)
		self._refresh_view()

	# ── Slots ──────────────────────────────────────────────────────────────────

	def _on_cell_clicked(self, cell2d: int) -> None:
		self._perturbed_cell = cell2d
		self._refresh_view()

	def _on_input_changed(self) -> None:
		if hasattr(self, "_preview_card"):
			self._preview_card.hide()

	def _on_focus_toggle(self) -> None:
		self._jac3d.set_focus_mode(self.btn_focus.isChecked())

	def _animate_card(self, widget: QWidget, delay_ms: int) -> None:
		from PySide6.QtWidgets import QGraphicsOpacityEffect
		from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QVariantAnimation

		eff = QGraphicsOpacityEffect(widget)
		widget.setGraphicsEffect(eff)
		eff.setOpacity(0.0)

		def start() -> None:
			anim = QPropertyAnimation(eff, b"opacity", widget)
			anim.setDuration(350)
			anim.setStartValue(0.0)
			anim.setEndValue(1.0)
			anim.setEasingCurve(QEasingCurve.Type.OutQuad)

			lay = widget.layout()
			if lay:
				lay.setContentsMargins(0, 12, 0, 0)
				margin_anim = QVariantAnimation(widget)
				margin_anim.setDuration(350)
				margin_anim.setStartValue(12)
				margin_anim.setEndValue(0)
				margin_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
				margin_anim.valueChanged.connect(
					lambda v: lay.setContentsMargins(0, v, 0, 0)
				)
				widget._margin_anim = margin_anim
				margin_anim.start()

			widget._opacity_anim = anim
			anim.start()

		if delay_ms > 0:
			QTimer.singleShot(delay_ms, start)
		else:
			start()

	def _set_row_mode(self, var: str, mode: str) -> None:
		if self._row_modes[var] == mode:
			return
		
		spn, auto_lbl = self._spins[var]
		current_val = spn.value()
		ref = self._auto_eps.get(var, 1.0) * 100.0  # reference value is auto_eps * 100
		
		self._row_modes[var] = mode
		
		btn_pct, btn_abs = self._row_toggles[var]
		btn_pct.blockSignals(True)
		btn_abs.blockSignals(True)
		
		if mode == "pct":
			btn_pct.setChecked(True)
			btn_abs.setChecked(False)
			auto_lbl.setText("Auto: 1.00%")
			spn.setRange(0.0001, 100.0)
			# Convert absolute value to percentage
			new_val = (current_val / ref * 100.0) if ref > 0 else 1.0
			spn.setValue(max(0.0001, min(100.0, new_val)))
		else:
			btn_pct.setChecked(False)
			btn_abs.setChecked(True)
			v = self._auto_eps.get(var, 1.0)
			if var == "P":
				auto_lbl.setText(f"Auto: {v:.2f} psia")
			else:
				auto_lbl.setText(f"Auto: {v:.5f}")
			spn.setRange(0.0001, 99999.0)
			# Convert percentage value to absolute
			new_val = current_val / 100.0 * ref
			spn.setValue(max(0.0001, min(99999.0, new_val)))
			
		btn_pct.blockSignals(False)
		btn_abs.blockSignals(False)
		self._on_input_changed()

	def _reset_to_auto(self, var: str) -> None:
		if var not in self._spins:
			return
		spn, _ = self._spins[var]
		if self._row_modes[var] == "pct":
			spn.setValue(1.0)
		else:
			spn.setValue(self._auto_eps.get(var, 1.0))
		self._on_input_changed()

	def _update_saved_deltas_display_from_config(self, pert: PerturbationConfig) -> None:
		confirmed = bool(
			self.project_config
			and self.project_config.constraints.perturbation_confirmed
			and pert
			and pert.perturbed_cell_id != 0
		)
		if confirmed:
			self._saved_status_chip.setText(f"Aktif untuk Run: Cell {pert.perturbed_cell_id}")
			self._saved_status_chip.setProperty("chipKind", "ok")
		else:
			self._saved_status_chip.setText("Belum Disimpan")
			self._saved_status_chip.setProperty("chipKind", "empty")
		self._saved_status_chip.style().unpolish(self._saved_status_chip)
		self._saved_status_chip.style().polish(self._saved_status_chip)

		is_saved = confirmed and pert.perturbed_cell_id == self._perturbed_cell
		if not is_saved:
			self._preview_card.hide()
			return

		self._preview_P.setText(f" dP  = {pert.delta_P:,.4f} psia")
		self._preview_Sw.setText(f" dSw = {pert.delta_Sw:.6f} (fraksi)")
		self._preview_Sg.setText(f" dSg = {pert.delta_Sg:.6f} (fraksi)")
		self._preview_card.show()

	def _on_save(self) -> None:
		def _delta(var: str) -> float:
			spn, _ = self._spins[var]
			if self._row_modes[var] == "pct":
				ref = self._auto_eps.get(var, 1.0) * 100.0
				return ref * spn.value() / 100.0
			return spn.value()

		pert = PerturbationConfig(
			perturbed_cell_id=self._perturbed_cell or 0,
			delta_P=_delta("P"),
			delta_Sw=_delta("Sw"),
			delta_Sg=_delta("Sg"),
		)
		self.project_config.perturbation = pert  # Update local config so the preview card updates correctly!
		self.perturbationChanged.emit(pert)
		self._update_saved_deltas_display_from_config(pert)

	def _toggle_panel(self) -> None:
		sizes = self.splitter.sizes()
		if len(sizes) < 2:
			return
		if hasattr(self, "_anim") and self._anim.state() == QVariantAnimation.State.Running:
			self._anim.stop()

		self._table_collapsed = not self._table_collapsed
		total_w = sizes[0] + sizes[1]
		if self._table_collapsed:
			self._saved_table_width = sizes[1] if sizes[1] > 0 else 400
			start_val, end_val = sizes[1], 0
			self.btn_toggle.setText("◀")
			self.btn_toggle.setToolTip("Show Details")
		else:
			start_val = sizes[1]
			end_val   = getattr(self, "_saved_table_width", 400) or 400
			self.btn_toggle.setText("▶")
			self.btn_toggle.setToolTip("Hide Details")

		self._anim = QVariantAnimation(self)
		self._anim.setDuration(300)
		self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
		self._anim.setStartValue(start_val)
		self._anim.setEndValue(end_val)
		self._anim.valueChanged.connect(
			lambda v: self.splitter.setSizes([total_w - v, v])
		)
		self._anim.start()

	# ── View refresh ───────────────────────────────────────────────────────────

	def _refresh_view(self) -> None:
		if self.project_config is None:
			return

		self._save_btn.setEnabled(self._perturbed_cell is not None)

		gs = self.project_config.grid_spec
		nx, ny, nz = gs.nx, gs.ny, getattr(gs, "nz", 1)
		plane      = nx * ny

		# Build connected set (3D, 1-indexed) for perturbed cell
		connected_set: set[int] = set()
		if self._perturbed_cell is not None and self._connections:
			perturbed_3d_0 = self._perturbed_cell - 1
			for conn in self._connections:
				if conn.from_cell_id == perturbed_3d_0:
					connected_set.add(conn.to_cell_id + 1)
				elif conn.to_cell_id == perturbed_3d_0:
					connected_set.add(conn.from_cell_id + 1)

		well_cells = {w.cell_id for w in self.project_config.wells}

		modes: dict[int, str] = {}
		if self._perturbed_cell is not None:
			modes[self._perturbed_cell] = "perturbed"
		for cell3d in connected_set:
			if cell3d != self._perturbed_cell:
				modes[cell3d] = "connected"
		for wc2d in well_cells:
			for iz in range(nz):
				wc3d = iz * plane + wc2d
				if wc3d not in modes:
					modes[wc3d] = "well"

		self._jac3d.set_grid(nx, ny, nz, modes, self._perturbed_cell)

		# Status bar
		if self._perturbed_cell:
			self._jac_status.setStyleSheet("""
				background-color: #DCEAF7; color: #0F5C8E;
				border: 1px solid #A9CCE5; border-radius: 8px;
				padding: 6px 14px; font-size: 9pt; font-weight: 600;
			""")
			n_entries = 1 + len(connected_set)
			if (self._perturbed_cell - 1) % plane + 1 in well_cells:
				n_entries += 1
			self._jac_status.setText(
				f"Perturb: Cell {self._perturbed_cell}  ·  P+Sw+Sg  "
				f"·  {n_entries} entri non-nol"
			)
		else:
			self._jac_status.setText(f"Grid {nx}×{ny}×{nz} — Pilih sel untuk inspeksi")

		# Rebuild scroll cards
		while self.scroll_layout.count() > 1:
			item = self.scroll_layout.takeAt(0)
			if item is not None:
				w = item.widget()
				if w is not None:
					w.hide()
					w.deleteLater()

		# Update preview card visibility
		if self.project_config:
			self._update_saved_deltas_display_from_config(self.project_config.perturbation)

		if self._perturbed_cell is None:
			self._cell_info_banner.hide()
			ph = QLabel(
				"Klik sel pada grid 3D untuk memilih titik perturbasi. "
				"Semua 3 variabel (P, Sw, Sg) akan diperturb serentak pada sel yang dipilih."
			)
			ph.setWordWrap(True)
			ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
			ph.setStyleSheet(
				"color: #5B6676; font-size: 10pt; font-style: italic; padding: 40px;"
			)
			self.scroll_layout.insertWidget(0, ph)
			return

		# Populate cell info banner
		perturbed_cell2d = (self._perturbed_cell - 1) % plane + 1
		well_in_cell = next(
			(w for w in self.project_config.wells if w.cell_id == perturbed_cell2d), None
		)
		n_conn = len(connected_set)
		n_ent  = 1 + n_conn + (1 if well_in_cell else 0)
		self._ci_cell_num.setText(f"Cell {self._perturbed_cell}")
		self._ci_conn_lbl.setText(f"{n_conn} koneksi  ·  {n_ent} entri non-nol")
		# Only surface the well line when there's actually a well to report —
		# an always-visible "Tidak ada sumur" placeholder was just noise for
		# the (common) case of a cell with no well.
		if well_in_cell:
			self._ci_well_lbl.setText(f"● Sumur: {well_in_cell.name}  ({well_in_cell.well_type})")
			self._ci_well_lbl.show()
		else:
			self._ci_well_lbl.hide()
		self._cell_info_banner.show()

		# Build entries
		entries = self._build_jacobian_entries(plane, nz, well_cells)
		for idx, entry in enumerate(entries):
			card = self._build_entry_card(entry)
			self.scroll_layout.insertWidget(idx, card)
			self._animate_card(card, idx * 80)

	# ── Jacobian structure computation ─────────────────────────────────────────

	def _build_jacobian_entries(
		self,
		plane: int,
		nz: int,
		well_cells: set[int],
	) -> list[dict]:
		assert self._perturbed_cell is not None
		assert self.project_config is not None

		gs  = self.project_config.grid_spec
		var = "P"  # display P column (all 3 vars perturbed simultaneously)
		sel = self._perturbed_cell          # cell3d, 1-indexed
		sel_0 = sel - 1                     # cell3d, 0-indexed

		sel_cell2d = (sel - 1) % plane + 1
		perturb_well = next(
			(w for w in self.project_config.wells if w.cell_id == sel_cell2d), None
		)

		entries: list[dict] = []

		# 1 ─ Self (diagonal) entry
		entries.append({
			"kind":      "self",
			"cell_id":   sel,
			"coords":    self._cell2d_coords(sel_cell2d, gs),
			"var":       var,
			"well":      perturb_well,
		})

		# 2 ─ Off-diagonal entries (grid connections)
		seen_nb: set[int] = set()
		for conn in self._connections:
			if conn.from_cell_id == sel_0:
				nb3d = conn.to_cell_id + 1      # cell3d, 1-indexed
			elif conn.to_cell_id == sel_0:
				nb3d = conn.from_cell_id + 1
			else:
				continue
			if nb3d == sel or nb3d in seen_nb:
				continue
			seen_nb.add(nb3d)

			nb2d = (nb3d - 1) % plane + 1
			nb_well = next(
				(w for w in self.project_config.wells if w.cell_id == nb2d), None
			)
			entries.append({
				"kind":             "connection",
				"cell_id":          nb3d,
				"coords":           self._cell2d_coords(nb2d, gs),
				"var":              var,
				"direction":        conn.direction,
				"transmissibility": conn.transmissibility,
				"area":             conn.area,
				"distance":         conn.distance,
				"well":             nb_well,
			})

		# 3 ─ Separate well-term card if this cell has a well
		#     (highlights that well modifies the diagonal differently from accumulation)
		if perturb_well is not None:
			entries.append({
				"kind": "well_term",
				"cell_id": sel,
				"var":  var,
				"well": perturb_well,
			})

		return entries

	def _cell2d_coords(self, cell2d: int, gs) -> tuple[int, int]:
		ix = (cell2d - 1) % gs.nx
		iy = (cell2d - 1) // gs.nx
		return ix, iy

	# ── Card builders ──────────────────────────────────────────────────────────

	def _build_entry_card(self, entry: dict) -> QWidget:
		kind = entry["kind"]
		var  = entry["var"]
		var_sym, var_color, var_name = _VAR_META[var]

		if kind == "self":
			return self._card_self(entry, var_sym, var_color, var_name)
		if kind == "connection":
			return self._card_connection(entry, var_sym, var_color)
		if kind == "well_term":
			return self._card_well_term(entry, var_sym, var_color)
		return QWidget()

	def _make_card(self, border_color: str) -> tuple[QWidget, QVBoxLayout]:
		# Wrapper widget to allow opacity animations while preserving shadow on the child card
		wrapper = QWidget()
		wrapper.setStyleSheet("background: transparent;")
		wrapper_lay = QVBoxLayout(wrapper)
		wrapper_lay.setContentsMargins(0, 0, 0, 0)
		wrapper_lay.setSpacing(0)

		card = QFrame()
		card.setObjectName("jacCard")
		card.setStyleSheet(f"""
			QFrame#jacCard {{
				background-color: #ffffff; border: 1.5px solid {border_color};
				border-radius: 8px;
			}}
		""")

		lay = QVBoxLayout(card)
		lay.setContentsMargins(12, 10, 12, 10)
		lay.setSpacing(6)
		
		wrapper_lay.addWidget(card)
		return wrapper, lay

	def _badge(self, text: str, bg: str, fg: str, border: str) -> QLabel:
		lbl = QLabel(text)
		lbl.setStyleSheet(f"""
			background-color: {bg}; color: {fg}; border: 1px solid {border};
			border-radius: 4px; padding: 2px 7px; font-size: 7.5pt; font-weight: 800;
		""")
		return lbl

	def _card_self(self, entry: dict, var_sym: str, var_color: str, var_name: str) -> QWidget:
		card, lay = self._make_card("#A9CCE5")  # light accent border

		cell_id = entry["cell_id"]
		ix, iy  = entry["coords"]
		well    = entry["well"]

		# Title row
		title_row = QHBoxLayout()
		title_row.setSpacing(8)
		title_lbl = QLabel(f"Cell {cell_id} ({ix}, {iy})  —  Diagonal")
		title_lbl.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #0C4A73;")
		title_row.addWidget(title_lbl)
		title_row.addStretch(1)
		title_row.addWidget(self._badge("SELF", "#DCEAF7", "#0F5C8E", "#A9CCE5"))
		lay.addLayout(title_row)

		if well:
			wtype = "Production" if well.well_type == "production" else "Injection"
			w_lbl = QLabel(f"Sumur: {well.name}  ({wtype})")
			w_lbl.setStyleSheet("font-size: 8pt; color: #0F5C8E; font-weight: 600;")
			lay.addWidget(w_lbl)

		return card

	def _card_connection(self, entry: dict, var_sym: str, var_color: str) -> QWidget:
		card, lay = self._make_card("#2D6A4F")  # success border

		cell_id = entry["cell_id"]
		ix, iy  = entry["coords"]
		direc   = entry["direction"]
		well    = entry["well"]
		arrow   = _DIR_ARROW.get(direc, "→")

		# Title row
		title_row = QHBoxLayout()
		title_row.setSpacing(8)
		title_lbl = QLabel(f"{arrow}  Cell {cell_id} ({ix}, {iy})  —  Off-Diagonal")
		title_lbl.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #1F4D38;")
		title_row.addWidget(title_lbl)
		title_row.addStretch(1)
		title_row.addWidget(self._badge(direc, "#DCEEE3", "#1F4D38", "#2D6A4F"))
		lay.addLayout(title_row)

		if well:
			w_note = QLabel(
				f"Sumur tetangga: {well.name}  ({'Prod' if well.well_type == 'production' else 'Inj'})"
			)
			w_note.setStyleSheet("font-size: 8pt; color: #A86A15; font-weight: 600;")
			lay.addWidget(w_note)

		return card

	def _card_well_term(self, entry: dict, var_sym: str, var_color: str) -> QWidget:
		card, lay = self._make_card("#A86A15")  # warning border

		well    = entry["well"]
		is_prod = well.well_type == "production"

		title_row = QHBoxLayout()
		title_row.setSpacing(8)
		icon  = "⚡" if is_prod else "💧"
		title = QLabel(f"{icon}  Well: {well.name}  —  Source/Sink Term")
		title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #6B4710;")
		title_row.addWidget(title)
		title_row.addStretch(1)
		wtype_badge = "PROD" if is_prod else "INJ"
		title_row.addWidget(self._badge(wtype_badge, "#F7E9D2", "#6B4710", "#A86A15"))
		lay.addLayout(title_row)

		# Well properties
		model_display = {
			"simple_flowrate": "Simple Flowrate",
			"peaceman": "Peaceman (analytical WI)",
		}.get(well.well_model, well.well_model)

		prop_row = QHBoxLayout()
		prop_row.setSpacing(16)

		def _kv(k: str, v: str) -> QLabel:
			lbl = QLabel(f"<b>{k}</b>  {v}")
			lbl.setStyleSheet("font-size: 8pt; color: #1F2937;")
			return lbl

		prop_row.addWidget(_kv("Model:", model_display))
		if well.well_model == "peaceman":
			prop_row.addWidget(_kv("BHP =", f"{well.bhp:,.1f} psia"))
		else:
			prop_row.addWidget(_kv("Q =", f"{well.flowrate:,.1f} STB/day"))
		prop_row.addStretch(1)
		lay.addLayout(prop_row)

		return card

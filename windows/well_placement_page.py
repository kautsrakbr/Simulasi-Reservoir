from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve, QPoint, QPointF, QRectF, QSize, QVariantAnimation, Signal
from PySide6.QtGui import (
	QBrush,
	QColor,
	QFont,
	QIcon,
	QLinearGradient,
	QPainter,
	QPen,
	QPixmap,
	QPolygonF,
)
from PySide6.QtWidgets import (
	QButtonGroup,
	QFrame,
	QGraphicsDropShadowEffect,
	QHBoxLayout,
	QInputDialog,
	QLabel,
	QLineEdit,
	QMenu,
	QPushButton,
	QScrollArea,
	QSplitter,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig, WellConfig
from windows.connectivity_3d_page import _Connectivity3DWidget


def _model_display(model: str) -> str:
	return {
		"simple_flowrate": "Simple Flowrate",
		"peaceman": "Peaceman",
		"well_model_3": "Model #3",
	}.get(model, model)


def _make_badge_icon(letter: str, color: str, size: int = 18) -> QIcon:
	"""Render a small filled circle with a bold letter, used as a segmented-button icon."""
	pix = QPixmap(size, size)
	pix.fill(Qt.GlobalColor.transparent)
	p = QPainter(pix)
	p.setRenderHint(QPainter.RenderHint.Antialiasing)
	p.setBrush(QBrush(QColor(color)))
	p.setPen(Qt.PenStyle.NoPen)
	p.drawEllipse(0, 0, size, size)
	f = QFont("Segoe UI", max(6, int(size * 0.46)))
	f.setBold(True)
	p.setFont(f)
	p.setPen(QColor("#ffffff"))
	p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
	p.end()
	return QIcon(pix)


class _WellPlacement3DWidget(_Connectivity3DWidget):
	"""Subclasses the connectivity viewer with production/injection colors."""

	cell_right_clicked = Signal(int, QPoint)  # (cell3d, globalPos) on right-click
	well_drag_moved    = Signal(int, int)     # (from_cell2d, to_cell3d) on drop
	escape_pressed     = Signal()

	_COLORS: dict[str, tuple] = {
		"normal":     ((247, 249, 251), (215, 222, 231)),
		"production": ((243, 228, 199), (183, 121,  31)),
		"injection":  ((220, 232, 242), ( 37,  99, 166)),
		"selected":   ((220, 234, 247), ( 15,  92, 142)),
		"moving":     ((247, 233, 210), (168, 106,  21)),
	}

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self._well_info: dict[int, tuple[str, str]] = {}
		self._move_mode_active: bool = False
		self._dragging_well: int | None = None   # cell2d being dragged
		self._drag_target:   int | None = None   # cell3d currently hovered over

	# ── helpers ──────────────────────────────────────────────────────────────

	def _cell_at(self, pt: QPointF) -> int | None:
		"""Return cell3d at widget position, or None."""
		if self._flat_mode:
			return self._flat_hit_test(pt)
		for c, poly in self._hit_polys:
			if poly.containsPoint(pt, Qt.FillRule.WindingFill):
				return c
		return None

	# ── mouse events ─────────────────────────────────────────────────────────

	def mousePressEvent(self, e) -> None:
		if e.button() == Qt.MouseButton.LeftButton and self._nx > 0:
			cell3d = self._cell_at(e.position())
			if cell3d is not None:
				plane   = self._nx * self._ny
				cell2d  = (cell3d - 1) % plane + 1
				if cell2d in self._well_info:
					# Start drag from this well
					self._dragging_well = cell2d
					self._drag_target   = cell3d
					self._drag_pos      = e.position()
					self._drag_btn      = Qt.MouseButton.LeftButton
					self._drag_moved    = False
					self.setCursor(Qt.CursorShape.ClosedHandCursor)
					return          # suppress base-class rotation
		super().mousePressEvent(e)

	def mouseMoveEvent(self, e) -> None:
		if self._dragging_well is not None:
			dp = e.position() - self._drag_pos
			if dp.manhattanLength() > 4:
				self._drag_moved = True
			new_target = self._cell_at(e.position())
			if new_target != self._drag_target:
				self._drag_target = new_target
				self._schedule_update()
			return

		# Hover cursor — show hand when over a well
		if self._drag_pos is None and self._nx > 0:
			cell3d = self._cell_at(e.position())
			if cell3d is not None:
				plane  = self._nx * self._ny
				cell2d = (cell3d - 1) % plane + 1
				cursor = (Qt.CursorShape.OpenHandCursor if cell2d in self._well_info
						  else Qt.CursorShape.ArrowCursor)
			else:
				cursor = Qt.CursorShape.ArrowCursor
			self.setCursor(cursor)

		super().mouseMoveEvent(e)

	def mouseReleaseEvent(self, e) -> None:
		if self._dragging_well is not None and e.button() == Qt.MouseButton.LeftButton:
			self.setCursor(Qt.CursorShape.ArrowCursor)
			if self._drag_moved and self._drag_target is not None:
				plane      = self._nx * self._ny
				target_c2d = (self._drag_target - 1) % plane + 1
				if (target_c2d != self._dragging_well
						and target_c2d not in self._well_info):
					self.well_drag_moved.emit(self._dragging_well, self._drag_target)
			elif not self._drag_moved and self._drag_target is not None:
				# Tap without drag → normal click select
				self.cell_clicked.emit(self._drag_target)
			self._dragging_well = None
			self._drag_target   = None
			self._drag_pos      = None
			self._drag_btn      = None
			self._drag_moved    = False
			self.update()
			return
		super().mouseReleaseEvent(e)

	def contextMenuEvent(self, e) -> None:
		pt   = QPointF(e.pos())
		cell = self._cell_at(pt)
		if cell is not None:
			self.cell_right_clicked.emit(cell, e.globalPos())
			e.accept()
		else:
			e.ignore()

	def keyPressEvent(self, e) -> None:
		if e.key() == Qt.Key.Key_Escape:
			self.escape_pressed.emit()
		else:
			super().keyPressEvent(e)

	def _draw_drag_target(self, p) -> None:
		"""Draw a drop-zone indicator on the hovered destination cell while dragging."""
		if self._dragging_well is None or self._drag_target is None or not self._drag_moved:
			return
		plane      = self._nx * self._ny
		target_c2d = (self._drag_target - 1) % plane + 1
		is_valid   = (target_c2d != self._dragging_well
					  and target_c2d not in self._well_info)
		fill_color  = QColor(15, 92, 142, 70)  if is_valid else QColor(178, 65, 63, 70)
		border_color = QColor("#0F5C8E")        if is_valid else QColor("#B2413F")
		label        = "✓"                      if is_valid else "✗"

		if self._flat_mode:
			c0 = (self._drag_target - 1) % plane
			ix = c0 % self._nx
			iy = c0 // self._nx
			cs = self._flat_cs
			rx = self._flat_x0 + ix * cs
			ry = self._flat_y0 + iy * cs
			p.setBrush(QBrush(fill_color))
			pen = QPen(border_color, max(1.5, cs * 0.07), Qt.PenStyle.DashLine)
			p.setPen(pen)
			p.drawRect(QRectF(rx, ry, cs, cs))
			if cs >= 18:
				p.setFont(QFont("Segoe UI", max(6, int(cs * 0.32))))
				p.setPen(border_color)
				p.drawText(QRectF(rx, ry, cs, cs), Qt.AlignmentFlag.AlignCenter, label)
		else:
			centre = self._top_face_centres.get(self._drag_target)
			if centre is not None:
				r = max(8, self._last_base_scale * 0.4)
				p.setBrush(QBrush(fill_color))
				p.setPen(QPen(border_color, 2.0, Qt.PenStyle.DashLine))
				p.drawEllipse(centre, r, r)
				p.setFont(QFont("Segoe UI", max(6, int(r * 0.7))))
				p.setPen(border_color)
				p.drawText(QRectF(centre.x()-r, centre.y()-r, r*2, r*2),
						   Qt.AlignmentFlag.AlignCenter, label)

	def _draw_well_pin(self, p, centre: QPointF, name: str, well_type: str,
					   is_sel: bool, scale: float, opacity: float = 1.0) -> None:
		"""Draw a single well pin at the given centre position."""
		pole_h = max(24, min(60, int(scale * 1.15)))
		head_r = max(7,  min(18, int(scale * 0.37)))
		pole_w = max(2.5, min(6.0, scale * 0.11))
		flag_h = max(18, min(36, int(scale * 0.68)))
		lbl_sz = max(7,  min(12, int(scale * 0.44)))
		lbl_font = QFont("Segoe UI Variable Text", lbl_sz); lbl_font.setBold(True)

		if well_type == "production":
			dark_col  = QColor("#6B4710"); main_col = QColor("#B7791F")
			light_col = QColor("#D9A14A"); glow_col = QColor(217, 161, 74, 90)
		else:
			dark_col  = QColor("#1B4566"); main_col = QColor("#2563A6")
			light_col = QColor("#5B8FC4"); glow_col = QColor(91, 143, 196, 90)

		if is_sel:
			main_col = main_col.lighter(135); light_col = light_col.lighter(120)
			dark_col = dark_col.lighter(130)

		p.setOpacity(opacity)
		x, y  = centre.x(), centre.y()
		top_y = y - pole_h
		tip   = QPointF(x, top_y)

		p.setBrush(QBrush(QColor(0, 0, 0, 38))); p.setPen(Qt.PenStyle.NoPen)
		p.drawEllipse(QPointF(x, y + 1.5), head_r * 0.95, head_r * 0.28)
		p.setBrush(QBrush(glow_col)); p.setPen(Qt.PenStyle.NoPen)
		p.drawEllipse(QPointF(x, y), head_r * 1.5, head_r * 0.45)

		pole_grad = QLinearGradient(x - pole_w, top_y, x + pole_w, y)
		pole_grad.setColorAt(0.0, light_col); pole_grad.setColorAt(1.0, dark_col)
		p.setBrush(QBrush(pole_grad)); p.setPen(Qt.PenStyle.NoPen)
		p.drawRoundedRect(QRectF(x - pole_w/2, top_y + head_r, pole_w, pole_h - head_r),
						  pole_w/2, pole_w/2)

		p.setBrush(QBrush(main_col))
		p.setPen(QPen(QColor("#ffffff"), max(1.5, pole_w * 0.55)))
		p.drawEllipse(tip, head_r, head_r)
		p.setBrush(QBrush(QColor(255, 255, 255, 160))); p.setPen(Qt.PenStyle.NoPen)
		spec_r = max(2, head_r // 3)
		p.drawEllipse(QPointF(x - head_r*0.30, top_y - head_r*0.30), spec_r, spec_r)

		icon_f = QFont("Segoe UI", max(5, head_r//2+1)); icon_f.setBold(True)
		p.setFont(icon_f); p.setPen(QColor("#ffffff"))
		p.drawText(QRectF(x-head_r, top_y-head_r, head_r*2, head_r*2),
				   Qt.AlignmentFlag.AlignCenter, "P" if well_type == "production" else "I")

		fm = p.fontMetrics(); p.setFont(lbl_font)
		tw = fm.horizontalAdvance(name)
		bw = max(tw+18, int(flag_h*2.2)); bh = flag_h
		bx = x + head_r*0.72;            by = top_y - bh/2
		p.setBrush(QBrush(QColor(0,0,0,28))); p.setPen(Qt.PenStyle.NoPen)
		p.drawRoundedRect(QRectF(bx+2, by+2, bw, bh), 6, 6)
		badge_grad = QLinearGradient(bx, by, bx, by+bh)
		badge_grad.setColorAt(0.0, light_col); badge_grad.setColorAt(1.0, dark_col)
		p.setBrush(QBrush(badge_grad)); p.setPen(QPen(QColor("#ffffff"), 1.2))
		p.drawRoundedRect(QRectF(bx, by, bw, bh), 6, 6)
		p.setFont(lbl_font); p.setPen(QColor("#ffffff"))
		p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, name)
		notch_cy = by + bh/2; notch_sz = max(4, bh//4)
		p.setBrush(QBrush(light_col)); p.setPen(Qt.PenStyle.NoPen)
		p.drawPolygon(QPolygonF([QPointF(bx, notch_cy),
								 QPointF(bx+notch_sz, notch_cy-notch_sz*0.6),
								 QPointF(bx+notch_sz, notch_cy+notch_sz*0.6)]))
		p.setOpacity(1.0)

	def _target_centre(self) -> QPointF | None:
		"""Compute screen position of the drag target cell centre."""
		if self._drag_target is None:
			return None
		plane = self._nx * self._ny
		if self._flat_mode:
			c0 = (self._drag_target - 1) % plane
			return QPointF(self._flat_x0 + (c0 % self._nx + 0.5) * self._flat_cs,
						   self._flat_y0 + (c0 // self._nx + 0.5) * self._flat_cs)
		return self._top_face_centres.get(self._drag_target)

	def _draw_overlay(self, p) -> None:
		if not self._well_info:
			return

		scale   = self._last_base_scale
		centres = self._top_face_centres
		plane   = self._nx * self._ny

		sel_cell2d: int | None = None
		if self._selected_cell is not None:
			sel_cell2d = (self._selected_cell - 1) % plane + 1

		# ── Draw each well pin ───────────────────────────────────────────────
		for cell2d, (name, well_type) in self._well_info.items():
			centre = None
			for _iz in range(self._nz - 1, -1, -1):
				centre = centres.get(_iz * plane + cell2d)
				if centre is not None:
					break
			if centre is None:
				continue

			is_dragging_this = (self._dragging_well == cell2d and self._drag_moved)
			opacity = 0.22 if is_dragging_this else 1.0   # ghost while dragging
			self._draw_well_pin(p, centre, name, well_type,
								is_sel=(sel_cell2d == cell2d),
								scale=scale, opacity=opacity)

		# ── Floating pin that follows the hovered cell during drag ───────────
		if self._dragging_well is not None and self._drag_moved:
			t_centre = self._target_centre()
			if t_centre is not None:
				t_c2d = (self._drag_target - 1) % plane + 1
				is_valid = (t_c2d != self._dragging_well
							and t_c2d not in self._well_info)
				name, well_type = self._well_info.get(self._dragging_well, ("?", "production"))
				# Draw cell highlight first
				self._draw_drag_target(p)
				# Then pin on top (slight scale-up to feel "lifted")
				if is_valid:
					self._draw_well_pin(p, t_centre, name, well_type,
										is_sel=True, scale=scale * 1.12)
			else:
				self._draw_drag_target(p)
		else:
			self._draw_drag_target(p)

	def _draw_hint(self, p, W: int, H: int) -> None:
		from PySide6.QtGui import QFont, QColor
		if self._move_mode_active:
			p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
			p.setPen(QColor("#A86A15"))
			hint = "MODE PINDAH  •  Klik sel tujuan untuk memindahkan  •  Esc: batal"
		else:
			p.setFont(QFont("Segoe UI", 7))
			p.setPen(QColor("#93A1B2"))
			if self._flat_mode:
				hint = "Klik: tambah/pilih  •  2x klik sumur: pindah  •  Drag: geser  •  Scroll: zoom"
			else:
				hint = "Klik: tambah/pilih  •  2x klik sumur: pindah  •  Drag: putar  •  Scroll: zoom"
		p.drawText(
			QRectF(8, H - 16, W - 16, 16),
			Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
			hint,
		)

	def _draw_legend(self, p) -> None:
		entries = [
			("Normal",     "normal"),
			("Production", "production"),
			("Injection",  "injection"),
			("Selected",   "selected"),
		]
		if self._move_mode_active:
			entries.append(("Mode Pindah", "moving"))
		x0, y0 = 12, 12
		p.setFont(QFont("Segoe UI", 8))
		for lbl, mode in entries:
			base_rgb, bdr_rgb = self._COLORS.get(mode, self._COLORS["normal"])
			p.setBrush(QBrush(QColor(*base_rgb)))
			p.setPen(QPen(QColor(*bdr_rgb), 1.5))
			p.drawRoundedRect(QRectF(x0, y0, 14, 14), 3, 3)
			p.setPen(QColor("#5B6676"))
			p.drawText(QRectF(x0 + 18, y0, 90, 14),
					   Qt.AlignmentFlag.AlignVCenter, lbl)
			y0 += 20
		if self._show_top_layer:
			p.setBrush(QBrush(QColor(247, 233, 210)))
			p.setPen(QPen(QColor(168, 106, 21), 1.5))
			p.drawRoundedRect(QRectF(x0, y0, 14, 14), 3, 3)
			p.setPen(QColor("#5B6676"))
			p.drawText(QRectF(x0 + 18, y0, 90, 14),
					   Qt.AlignmentFlag.AlignVCenter, "Top Layer")
			y0 += 20


_SEG_CONTAINER_QSS = """
QWidget#segContainer {
	background-color: #F1F4F8;
	border-radius: 10px;
}
"""

_SEG_BASE = """
QPushButton {
	background-color: transparent;
	color: #5B6676;
	border: 1px solid transparent;
	border-radius: 8px;
	padding: 7px 12px;
	font-size: 8.5pt;
	font-weight: 600;
	min-height: 30px;
}
QPushButton:hover { background-color: #D7DEE7; color: #1F2937; }
QPushButton:checked {
	background-color: #ffffff;
	color: #1F2937;
	font-weight: 700;
	border: 1px solid #D7DEE7;
}
QPushButton:checked:hover { background-color: #ffffff; }
"""


class WellPlacementPage(QWidget):
	wellsChanged = Signal(list)  # emits list[WellConfig] on Save Changes

	def __init__(self) -> None:
		super().__init__()
		self.project_config: ProjectConfig | None = None
		self._pending_wells: list[WellConfig] = []
		self._selected_well_cell: int | None = None
		self._moving_well_cell: int | None = None   # cell2d of well in Move Mode
		self._table_collapsed = False
		self._saved_table_width = 380

		root = QVBoxLayout(self)
		root.setSpacing(0)
		root.setContentsMargins(0, 0, 0, 0)

		# ── Splitter ────────────────────────────────────────────────────────────
		self.splitter = QSplitter(Qt.Orientation.Horizontal)
		self.splitter.setObjectName("wellSplitter")
		self.splitter.setStyleSheet(
			"QSplitter::handle { background-color: #D7DEE7; height: 1px; width: 1px; }"
		)

		# ── Left panel ─────────────────────────────────────────────────────────
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		left_layout.setContentsMargins(0, 0, 0, 0)
		left_layout.setSpacing(0)

		toolbar = QWidget()
		toolbar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #D7DEE7;")
		tbar = QHBoxLayout(toolbar)
		tbar.setContentsMargins(16, 8, 16, 8)
		tbar.setSpacing(14)

		title_lbl = QLabel("Well Placement")
		title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #0F5C8E;")
		tbar.addWidget(title_lbl)
		tbar.addStretch(1)

		self._well_status = QLabel("Grid belum dikonfigurasi.")
		self._well_status.setStyleSheet("""
			background-color: #DCEAF7; color: #0F5C8E;
			border: 1px solid #A9CCE5; border-radius: 8px;
			padding: 6px 14px; font-size: 9pt; font-weight: 600;
		""")
		tbar.addWidget(self._well_status)

		btn_reset = QPushButton("  ↺  Reset View")
		btn_reset.setStyleSheet("""
			QPushButton { background-color:#ffffff; color:#5B6676; border:1px solid #D7DEE7;
				border-radius:6px; padding:5px 12px; font-size:9pt; font-weight:600; }
			QPushButton:hover { background-color:#F7F9FB; border-color:#0F5C8E; color:#0F5C8E; }
		""")
		btn_reset.clicked.connect(lambda: self._well3d.reset_view())
		tbar.addWidget(btn_reset)

		self.btn_top_layer = QPushButton("  Top Layer")
		self.btn_top_layer.setCheckable(True)
		self.btn_top_layer.setChecked(False)
		self.btn_top_layer.setStyleSheet("""
			QPushButton { background-color:#ffffff; color:#5B6676; border:1px solid #D7DEE7;
				border-radius:6px; padding:5px 12px; font-size:9pt; font-weight:600; }
			QPushButton:hover { background-color:#F7E9D2; border-color:#A86A15; color:#6B4710; }
			QPushButton:checked { background-color:#F7E9D2; border-color:#A86A15; color:#6B4710;
				font-weight: 700; }
		""")
		self.btn_top_layer.toggled.connect(self._on_top_layer_toggled)
		tbar.addWidget(self.btn_top_layer)

		self.btn_toggle_table = QPushButton("▶")
		self.btn_toggle_table.setFixedSize(34, 34)
		self.btn_toggle_table.setToolTip("Hide Details")
		self.btn_toggle_table.setStyleSheet("""
			QPushButton { background-color:#ffffff; color:#5B6676; border:1px solid #D7DEE7;
				border-radius:6px; font-size:11pt; font-weight:bold; padding:0px; }
			QPushButton:hover { background-color:#F7F9FB; border-color:#0F5C8E; color:#0F5C8E; }
		""")
		self.btn_toggle_table.clicked.connect(self._toggle_table_panel)
		tbar.addWidget(self.btn_toggle_table)

		left_layout.addWidget(toolbar)

		left_content = QWidget()
		left_content_layout = QVBoxLayout(left_content)
		left_content_layout.setContentsMargins(12, 12, 6, 12)
		left_content_layout.setSpacing(0)

		self._well3d = _WellPlacement3DWidget()
		self._well3d.cell_clicked.connect(self._on_cell_clicked)
		self._well3d.cell_right_clicked.connect(self._on_cell_right_clicked)
		self._well3d.well_drag_moved.connect(self._on_well_drag_moved)
		self._well3d.escape_pressed.connect(self._cancel_move_mode)
		left_content_layout.addWidget(self._well3d, 1)
		left_layout.addWidget(left_content, 1)

		# ── Right panel ────────────────────────────────────────────────────────
		self.right_panel = QWidget()
		self.right_panel.setStyleSheet("background-color: #F7F9FB;")
		right_layout = QVBoxLayout(self.right_panel)
		right_layout.setContentsMargins(0, 0, 0, 0)
		right_layout.setSpacing(0)

		right_header = QWidget()
		right_header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #D7DEE7;")
		rh = QHBoxLayout(right_header)
		rh.setContentsMargins(16, 8, 16, 8)
		QLabel_w = QLabel("Well List")
		QLabel_w.setStyleSheet(
			"font-size: 11pt; font-weight: 700; color: #1F2937; letter-spacing: 0.5px;"
		)
		rh.addWidget(QLabel_w)
		rh.addStretch(1)
		right_layout.addWidget(right_header)

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
		self.scroll_layout.setSpacing(10)
		self.scroll_layout.addStretch(1)

		self.scroll_area.setWidget(self.scroll_content)
		rc_layout.addWidget(self.scroll_area, stretch=1)
		right_layout.addWidget(right_content, stretch=1)

		# ── Bottom controls ────────────────────────────────────────────────────
		bottom = QWidget()
		bottom.setObjectName("bottomPanel")
		bottom.setStyleSheet("""
			QWidget#bottomPanel {
				background-color: #ffffff;
				border-top: 1px solid #D7DEE7;
				border-top-left-radius: 14px; border-top-right-radius: 14px;
			}
		""")
		bottom_shadow = QGraphicsDropShadowEffect(bottom)
		bottom_shadow.setBlurRadius(24)
		bottom_shadow.setColor(QColor(15, 23, 42, 35))
		bottom_shadow.setOffset(0, -3)
		bottom.setGraphicsEffect(bottom_shadow)

		bot_layout = QVBoxLayout(bottom)
		bot_layout.setContentsMargins(16, 16, 16, 16)
		bot_layout.setSpacing(7)

		# Well type
		type_lbl = QLabel("WELL TYPE")
		type_lbl.setStyleSheet(
			"font-size: 7.5pt; font-weight: 700; color: #93A1B2; letter-spacing: 1.2px;"
		)
		bot_layout.addWidget(type_lbl)

		type_seg = QWidget()
		type_seg.setObjectName("segContainer")
		type_seg.setStyleSheet(_SEG_CONTAINER_QSS)
		type_seg_layout = QHBoxLayout(type_seg)
		type_seg_layout.setContentsMargins(3, 3, 3, 3)
		type_seg_layout.setSpacing(2)

		self.btn_prod = QPushButton("Production")
		self.btn_prod.setIcon(_make_badge_icon("P", "#B7791F"))
		self.btn_inj = QPushButton("Injection")
		self.btn_inj.setIcon(_make_badge_icon("I", "#2563A6"))
		for btn in (self.btn_prod, self.btn_inj):
			btn.setCheckable(True)
			btn.setIconSize(QSize(16, 16))
			btn.setCursor(Qt.CursorShape.PointingHandCursor)
			btn.setStyleSheet(_SEG_BASE)
			type_seg_layout.addWidget(btn)

		self.type_group = QButtonGroup(self)
		self.type_group.addButton(self.btn_prod)
		self.type_group.addButton(self.btn_inj)
		self.type_group.setExclusive(True)
		self.btn_prod.setChecked(True)
		bot_layout.addWidget(type_seg)

		# Well model
		model_lbl = QLabel("WELL MODEL")
		model_lbl.setStyleSheet(
			"font-size: 7.5pt; font-weight: 700; color: #93A1B2; letter-spacing: 1.2px; margin-top: 6px;"
		)
		bot_layout.addWidget(model_lbl)

		model_seg = QWidget()
		model_seg.setObjectName("segContainer")
		model_seg.setStyleSheet(_SEG_CONTAINER_QSS)
		model_seg_layout = QHBoxLayout(model_seg)
		model_seg_layout.setContentsMargins(3, 3, 3, 3)
		model_seg_layout.setSpacing(2)

		self.btn_simple = QPushButton("Simple Flowrate")
		self.btn_simple.setIcon(_make_badge_icon("S", "#0F5C8E"))
		self.btn_peaceman = QPushButton("Peaceman")
		self.btn_peaceman.setIcon(_make_badge_icon("P", "#0F5C8E"))
		self.btn_model3 = QPushButton("Model #3")
		self.btn_model3.setIcon(_make_badge_icon("3", "#0F5C8E"))
		for btn in (self.btn_simple, self.btn_peaceman, self.btn_model3):
			btn.setCheckable(True)
			btn.setIconSize(QSize(16, 16))
			btn.setCursor(Qt.CursorShape.PointingHandCursor)
			btn.setStyleSheet(_SEG_BASE)
			model_seg_layout.addWidget(btn)

		self.model_group = QButtonGroup(self)
		self.model_group.addButton(self.btn_simple)
		self.model_group.addButton(self.btn_peaceman)
		self.model_group.addButton(self.btn_model3)
		self.model_group.setExclusive(True)
		self.btn_simple.setChecked(True)
		bot_layout.addWidget(model_seg)

		# Save Changes button
		self.btn_save = QPushButton("✓   Save Changes")
		self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
		self.btn_save.setStyleSheet("""
			QPushButton {
				background-color: #0F5C8E;
				color: #ffffff; border: none;
				border-radius: 9px; padding: 10px 18px;
				font-size: 9.5pt; font-weight: 700; min-height: 38px; margin-top: 10px;
				letter-spacing: 0.3px;
			}
			QPushButton:hover {
				background-color: #2E7DAE;
			}
			QPushButton:pressed { background-color: #0C4A73; }
		""")
		self.btn_save.clicked.connect(self._on_save_changes)
		bot_layout.addWidget(self.btn_save)

		right_layout.addWidget(bottom)

		self.splitter.addWidget(left_panel)
		self.splitter.addWidget(self.right_panel)
		self.splitter.setStretchFactor(0, 3)
		self.splitter.setStretchFactor(1, 2)
		self.splitter.setSizes([620, 380])

		root.addWidget(self.splitter, stretch=1)

	# ── Public API ──────────────────────────────────────────────────────────────

	def set_project(self, project_config: ProjectConfig) -> None:
		self.project_config = project_config
		gs = project_config.grid_spec
		self._well3d._nx = gs.nx
		self._well3d._ny = gs.ny
		self._well3d._nz = getattr(gs, "nz", 1)
		self._pending_wells = list(project_config.wells)
		self._selected_well_cell = None
		self._refresh_well_view()

	# ── Internal slots ──────────────────────────────────────────────────────────

	def _on_cell_clicked(self, cell3d: int) -> None:
		gs = self.project_config.grid_spec
		nx = gs.nx
		plane = nx * gs.ny
		cell2d = (cell3d - 1) % plane + 1

		# ── Move Mode: next left-click is the destination ─────────────────────
		if self._moving_well_cell is not None:
			if cell2d == self._moving_well_cell:
				self._cancel_move_mode()
			else:
				target_occupied = any(w.cell_id == cell2d for w in self._pending_wells)
				if not target_occupied:
					for w in self._pending_wells:
						if w.cell_id == self._moving_well_cell:
							w.cell_id = cell2d
							break
					self._selected_well_cell = cell2d
					self._moving_well_cell = None
					self._refresh_well_view()
			return

		# ── Normal Mode ───────────────────────────────────────────────────────
		existing = next((w for w in self._pending_wells if w.cell_id == cell2d), None)
		if existing is None:
			well_type = "production" if self.btn_prod.isChecked() else "injection"
			model = self._get_selected_model()
			prefix = "PROD" if well_type == "production" else "INJ"
			count = sum(1 for w in self._pending_wells if w.well_type == well_type) + 1
			self._pending_wells.append(WellConfig(
				name=f"{prefix}-{count}",
				well_type=well_type,
				cell_id=cell2d,
				well_model=model,
				flowrate=100.0,
			))
			self._selected_well_cell = cell2d
		else:
			self._selected_well_cell = cell2d
		self._refresh_well_view()

	def _on_cell_right_clicked(self, cell3d: int, pos: QPoint) -> None:
		if self.project_config is None:
			return
		gs = self.project_config.grid_spec
		plane = gs.nx * gs.ny
		cell2d = (cell3d - 1) % plane + 1
		well = next((w for w in self._pending_wells if w.cell_id == cell2d), None)
		if well is None:
			return
		self._show_well_menu(well, pos)

	def _show_well_menu(self, well: WellConfig, global_pos: QPoint) -> None:
		"""Build and execute the well actions menu (used by both the 3D view and the well cards)."""
		cell_id = well.cell_id
		self._selected_well_cell = cell_id
		self._refresh_well_view()

		menu = QMenu(self)
		menu.setStyleSheet("""
			QMenu {
				background-color: #ffffff;
				border: 1px solid #D7DEE7;
				border-radius: 8px;
				padding: 4px;
				font-size: 9.5pt;
			}
			QMenu::item {
				padding: 9px 18px 9px 12px;
				border-radius: 5px;
				color: #1F2937;
				min-width: 160px;
			}
			QMenu::item:selected { background-color: #EEF2F6; }
			QMenu::separator { height: 1px; background: #D7DEE7; margin: 3px 8px; }
		""")

		other_type  = "injection" if well.well_type == "production" else "production"
		other_label = "Injection" if other_type == "injection" else "Production"

		act_flowrate = menu.addAction(f"  Ubah Flowrate  ({well.flowrate:.0f} STB/day)")
		act_switch   = menu.addAction(f"  Ubah ke {other_label}")
		act_move     = menu.addAction(f"  Pindahkan  {well.name}")
		menu.addSeparator()
		act_delete   = menu.addAction(f"  Hapus  {well.name}")

		action = menu.exec(global_pos)

		if action == act_delete:
			self._remove_well(cell_id)
		elif action == act_switch:
			self._switch_well_type(cell_id, other_type)
		elif action == act_move:
			self._moving_well_cell = cell_id
			self._refresh_well_view()
		elif action == act_flowrate:
			self._show_flowrate_dialog(cell_id, well)

	def _switch_well_type(self, cell_id: int, new_type: str) -> None:
		for w in self._pending_wells:
			if w.cell_id == cell_id:
				w.well_type = new_type
				break
		self._refresh_well_view()

	def _show_flowrate_dialog(self, cell2d: int, well: WellConfig) -> None:
		val, ok = QInputDialog.getDouble(
			self,
			f"Ubah Flowrate — {well.name}",
			"Flowrate (STB/day):",
			well.flowrate,
			0.0,
			999_999.0,
			1,
		)
		if ok:
			well.flowrate = val
			self._refresh_well_view()

	def _on_well_drag_moved(self, from_cell2d: int, to_cell3d: int) -> None:
		gs    = self.project_config.grid_spec
		plane = gs.nx * gs.ny
		to_c2d = (to_cell3d - 1) % plane + 1
		for w in self._pending_wells:
			if w.cell_id == from_cell2d:
				w.cell_id = to_c2d
				break
		self._selected_well_cell = to_c2d
		self._refresh_well_view()

	def _cancel_move_mode(self) -> None:
		if self._moving_well_cell is not None:
			self._moving_well_cell = None
			self._refresh_well_view()

	def _get_selected_model(self) -> str:
		if self.btn_peaceman.isChecked():
			return "peaceman"
		if self.btn_model3.isChecked():
			return "well_model_3"
		return "simple_flowrate"

	def _on_top_layer_toggled(self, checked: bool) -> None:
		self._well3d.set_show_top_layer(checked)

	def _remove_well(self, cell_id: int) -> None:
		self._pending_wells = [w for w in self._pending_wells if w.cell_id != cell_id]
		if self._selected_well_cell == cell_id:
			self._selected_well_cell = None
		self._refresh_well_view()

	def _rename_well(self, cell_id: int, new_name: str) -> None:
		for w in self._pending_wells:
			if w.cell_id == cell_id:
				w.name = new_name
				break
		# Refresh only the 3D overlay (don't rebuild cards — user is still typing)
		self._well3d._well_info = {
			w.cell_id: (w.name, w.well_type) for w in self._pending_wells
		}
		self._well3d.update()

	def _on_save_changes(self) -> None:
		self.wellsChanged.emit(list(self._pending_wells))

	def _toggle_table_panel(self) -> None:
		sizes = self.splitter.sizes()
		if len(sizes) < 2:
			return
		if hasattr(self, "_splitter_animation") and \
				self._splitter_animation.state() == QVariantAnimation.State.Running:
			self._splitter_animation.stop()

		self._table_collapsed = not self._table_collapsed
		total_w = sizes[0] + sizes[1]
		if self._table_collapsed:
			self._saved_table_width = sizes[1] if sizes[1] > 0 else 380
			start_val, end_val = sizes[1], 0
			self.btn_toggle_table.setText("◀")
			self.btn_toggle_table.setToolTip("Show Details")
		else:
			start_val = sizes[1]
			end_val = getattr(self, "_saved_table_width", 380) or 380
			self.btn_toggle_table.setText("▶")
			self.btn_toggle_table.setToolTip("Hide Details")

		self._splitter_animation = QVariantAnimation(self)
		self._splitter_animation.setDuration(300)
		self._splitter_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
		self._splitter_animation.setStartValue(start_val)
		self._splitter_animation.setEndValue(end_val)
		self._splitter_animation.valueChanged.connect(
			lambda val: self.splitter.setSizes([total_w - val, val])
		)
		self._splitter_animation.start()

	# ── View refresh ────────────────────────────────────────────────────────────

	def _refresh_well_view(self) -> None:
		if self.project_config is None:
			return
		gs = self.project_config.grid_spec
		nx, ny, nz = gs.nx, gs.ny, getattr(gs, "nz", 1)

		modes: dict[int, str] = {}
		for w in self._pending_wells:
			if w.cell_id == self._moving_well_cell:
				cell_mode = "moving"
			elif w.cell_id == self._selected_well_cell:
				cell_mode = "selected"
			else:
				cell_mode = w.well_type
			for iz in range(nz):
				cell3d = iz * nx * ny + w.cell_id
				modes[cell3d] = cell_mode

		self._well3d._well_info = {
			w.cell_id: (w.name, w.well_type) for w in self._pending_wells
		}
		self._well3d._move_mode_active = self._moving_well_cell is not None
		sel3d = (nz - 1) * nx * ny + self._selected_well_cell if self._selected_well_cell else None
		self._well3d.set_grid(nx, ny, nz, modes, sel3d)

		n_prod = sum(1 for w in self._pending_wells if w.well_type == "production")
		n_inj  = sum(1 for w in self._pending_wells if w.well_type == "injection")
		if self._moving_well_cell is not None:
			moving_name = next(
				(w.name for w in self._pending_wells if w.cell_id == self._moving_well_cell), "?"
			)
			self._well_status.setText(
				f"MODE PINDAH: {moving_name}  ·  Klik sel tujuan  ·  Esc untuk batal"
			)
			self._well_status.setStyleSheet("""
				background-color: #F7E9D2; color: #6B4710;
				border: 1px solid #A86A15; border-radius: 8px;
				padding: 6px 14px; font-size: 9pt; font-weight: 700;
			""")
		else:
			self._well_status.setText(
				f"Grid {nx}×{ny}×{nz}  ·  {n_prod} Prod  ·  {n_inj} Inj"
			)
			self._well_status.setStyleSheet("""
				background-color: #DCEAF7; color: #0F5C8E;
				border: 1px solid #A9CCE5; border-radius: 8px;
				padding: 6px 14px; font-size: 9pt; font-weight: 600;
			""")

		# Rebuild well cards
		while self.scroll_layout.count() > 1:
			item = self.scroll_layout.takeAt(0)
			if item is not None:
				w = item.widget()
				if w is not None:
					w.hide()
					w.deleteLater()

		if not self._pending_wells:
			ph = QLabel("Klik sel pada grid 3D untuk menempatkan sumur.")
			ph.setWordWrap(True)
			ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
			ph.setStyleSheet(
				"color: #5B6676; font-size: 10pt; font-style: italic; padding: 40px;"
			)
			self.scroll_layout.insertWidget(0, ph)
			return

		for idx, well in enumerate(self._pending_wells):
			card = self._build_well_card(well)
			self.scroll_layout.insertWidget(idx, card)

	def _build_well_card(self, well: WellConfig) -> QFrame:
		is_prod = well.well_type == "production"
		is_sel = well.cell_id == self._selected_well_cell
		type_color = "#B7791F" if is_prod else "#2563A6"

		card = QFrame()
		card.setObjectName("wellCard")
		card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		border_color = "#0F5C8E" if is_sel else "#D7DEE7"
		card.setStyleSheet(f"""
			QFrame#wellCard {{
				background-color: #ffffff;
				border: 1.5px solid {border_color};
				border-radius: 8px;
			}}
			QFrame#wellCard:hover {{
				border-color: {'#0F5C8E' if is_sel else '#B8C3D1'};
				background-color: #F7F9FB;
			}}
		""")

		card_layout = QVBoxLayout(card)
		card_layout.setContentsMargins(12, 10, 12, 10)
		card_layout.setSpacing(6)

		# Header: name + type label
		header_row = QHBoxLayout()
		header_row.setSpacing(8)

		name_edit = QLineEdit(well.name)
		name_edit.setStyleSheet("""
			QLineEdit { font-size: 10pt; font-weight: 700; color: #1F2937;
				border: none; border-bottom: 1.5px solid transparent;
				background: transparent; padding: 1px 2px; }
			QLineEdit:focus { border-bottom-color: #0F5C8E; background: #DCEAF7; }
		""")
		name_edit.textChanged.connect(
			lambda text, cid=well.cell_id: self._rename_well(cid, text)
		)
		header_row.addWidget(name_edit, 1)

		type_lbl = QLabel("Production" if is_prod else "Injection")
		type_lbl.setStyleSheet(f"font-size: 8pt; font-weight: 700; color: {type_color};")
		header_row.addWidget(type_lbl)
		card_layout.addLayout(header_row)

		# Cell location + model + flowrate (read-only — edit via right-click menu)
		info_lbl = QLabel(
			f"Cell ID: {well.cell_id}  ·  {_model_display(well.well_model)}  ·  "
			f"{well.flowrate:.0f} STB/day"
		)
		info_lbl.setStyleSheet("font-size: 8.5pt; color: #5B6676;")
		card_layout.addWidget(info_lbl)

		hint_lbl = QLabel("Klik kanan untuk opsi")
		hint_lbl.setStyleSheet("font-size: 7.5pt; color: #93A1B2; font-style: italic;")
		card_layout.addWidget(hint_lbl)

		card.customContextMenuRequested.connect(
			lambda pos, w=well, c=card: self._show_well_menu(w, c.mapToGlobal(pos))
		)

		return card

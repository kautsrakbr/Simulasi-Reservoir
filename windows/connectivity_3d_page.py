from __future__ import annotations

import math
from PySide6.QtCore import Qt, QPointF, Signal, QRectF, QSize, Property, QVariantAnimation, QParallelAnimationGroup, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPolygonF, QBrush, QPen
from PySide6.QtWidgets import (
	QHBoxLayout,
	QLabel,
	QPushButton,
	QVBoxLayout,
	QWidget,
	QSplitter,
	QScrollArea,
	QFrame,
	QGridLayout,
	QButtonGroup,
	QGraphicsDropShadowEffect,
)

from engine.domain.project import ProjectConfig
from engine.grid.builder import build_grid
from engine.physics.transmissibility import update_grid_transmissibility


def _symmetric_cells(n: int, well: int, nx: int, ny: int) -> list[int]:
	"""Return 1-indexed cells symmetric to n about well in the XY plane."""
	nr, nc = divmod(n - 1, nx)
	wr, wc = divmod(well - 1, nx)
	dr, dc = nr - wr, nc - wc
	result: set[int] = set()
	for tr, tc in [
		(dr, dc),
		(-dr, dc),
		(dr, -dc),
		(-dr, -dc),
		(dc, dr),
		(-dc, dr),
		(dc, -dr),
		(-dc, -dr),
	]:
		r2, c2 = wr + tr, wc + tc
		if 0 <= r2 < ny and 0 <= c2 < nx:
			m = r2 * nx + c2 + 1
			if m != n:
				result.add(m)
	return sorted(result)


class _Connectivity3DWidget(QWidget):
	"""
	Interactive 3D reservoir-grid viewer rendered with QPainter.

	Left-drag   → azimuth / elevation rotation
	Scroll      → zoom
	Middle-drag → pan
	Dbl-click   → reset view
	Click       → select cell (emits cell_clicked)
	"""

	cell_clicked = Signal(int)   # emits cell2d (1-based) on left-click

	# Face definitions: (outward_normal_xyz, vertex_indices, brightness)
	_FACES = [
		((0,  1,  0), [3, 7, 6, 2], 1.00),   # top    y+
		((0,  0,  1), [4, 5, 6, 7], 0.85),   # front  z+
		((1,  0,  0), [1, 2, 6, 5], 0.70),   # right  x+
		((-1, 0,  0), [0, 4, 7, 3], 0.60),   # left   x-
		((0,  0, -1), [0, 3, 2, 1], 0.55),   # back   z-
		((0, -1,  0), [0, 1, 5, 4], 0.40),   # bottom y-
	]

	# Mode colors: (fill_rgb, border_rgb)
	_COLORS: dict[str, tuple] = {
		"normal":    ((248, 250, 252), (203, 213, 225)),
		"symmetric": ((209, 250, 229), ( 16, 185, 129)),
		"well":      ((254, 243, 199), (245, 158,  11)),
		"selected":  ((207, 250, 254), (  8, 145, 178)),
	}

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._nx = self._ny = self._nz = 0
		self._cell_modes: dict[int, str] = {}
		self._az = 30.0
		self._el = 25.0
		self._zoom = 1.0
		self._pan_x = self._pan_y = 0.0
		self._drag_btn: Qt.MouseButton | None = None
		self._drag_pos: QPointF | None = None
		self._drag_az = 30.0
		self._drag_el = 25.0
		self._drag_px = self._drag_py = 0.0
		self._drag_moved = False
		self._hit_polys: list[tuple[int, QPolygonF]] = []
		self._selected_cell: int | None = None
		self.setMinimumSize(300, 260)
		self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

	# ── PySide Property definitions for smooth animation ────────────────────────

	def get_az(self) -> float:
		return self._az
	def set_az(self, val: float) -> None:
		self._az = val
		self.update()
	azimuth = Property(float, get_az, set_az)

	def get_el(self) -> float:
		return self._el
	def set_el(self, val: float) -> None:
		self._el = val
		self.update()
	elevation = Property(float, get_el, set_el)

	def get_zoom(self) -> float:
		return self._zoom
	def set_zoom(self, val: float) -> None:
		self._zoom = val
		self.update()
	zoom_val = Property(float, get_zoom, set_zoom)

	def get_pan_x(self) -> float:
		return self._pan_x
	def set_pan_x(self, val: float) -> None:
		self._pan_x = val
		self.update()
	pan_x = Property(float, get_pan_x, set_pan_x)

	def get_pan_y(self) -> float:
		return self._pan_y
	def set_pan_y(self, val: float) -> None:
		self._pan_y = val
		self.update()
	pan_y = Property(float, get_pan_y, set_pan_y)

	def set_grid(self, nx: int, ny: int, nz: int,
				 cell_modes: dict[int, str],
				 selected_cell: int | None = None) -> None:
		self._nx, self._ny, self._nz = nx, ny, nz
		self._cell_modes = cell_modes
		self._selected_cell = selected_cell
		self.update()

	def set_selected_cell(self, cell2d: int | None) -> None:
		self._selected_cell = cell2d
		self.update()

	def reset_view(self) -> None:
		if hasattr(self, "_anim_group") and self._anim_group.state() == QParallelAnimationGroup.State.Running:
			self._anim_group.stop()

		dim = max(self._nx, self._ny, self._nz, 1)
		target_zoom = max(0.1, min(2.0, 2.0 / dim))

		# Setup parallel animation group for camera variables
		self.anim_az = QPropertyAnimation(self, b"azimuth")
		self.anim_az.setDuration(500)
		self.anim_az.setStartValue(self._az)
		self.anim_az.setEndValue(30.0)
		self.anim_az.setEasingCurve(QEasingCurve.Type.InOutQuad)

		self.anim_el = QPropertyAnimation(self, b"elevation")
		self.anim_el.setDuration(500)
		self.anim_el.setStartValue(self._el)
		self.anim_el.setEndValue(25.0)
		self.anim_el.setEasingCurve(QEasingCurve.Type.InOutQuad)

		self.anim_zoom = QPropertyAnimation(self, b"zoom_val")
		self.anim_zoom.setDuration(500)
		self.anim_zoom.setStartValue(self._zoom)
		self.anim_zoom.setEndValue(target_zoom)
		self.anim_zoom.setEasingCurve(QEasingCurve.Type.InOutQuad)

		self.anim_px = QPropertyAnimation(self, b"pan_x")
		self.anim_px.setDuration(500)
		self.anim_px.setStartValue(self._pan_x)
		self.anim_px.setEndValue(0.0)
		self.anim_px.setEasingCurve(QEasingCurve.Type.InOutQuad)

		self.anim_py = QPropertyAnimation(self, b"pan_y")
		self.anim_py.setDuration(500)
		self.anim_py.setStartValue(self._pan_y)
		self.anim_py.setEndValue(0.0)
		self.anim_py.setEasingCurve(QEasingCurve.Type.InOutQuad)

		self._anim_group = QParallelAnimationGroup(self)
		self._anim_group.addAnimation(self.anim_az)
		self._anim_group.addAnimation(self.anim_el)
		self._anim_group.addAnimation(self.anim_zoom)
		self._anim_group.addAnimation(self.anim_px)
		self._anim_group.addAnimation(self.anim_py)
		self._anim_group.start()

	def _reset_view(self) -> None:
		self._az, self._el = 30.0, 25.0
		self._pan_x = self._pan_y = 0.0
		dim = max(self._nx, self._ny, self._nz, 1)
		self._zoom = max(0.1, min(2.0, 2.0 / dim))

	def mousePressEvent(self, e) -> None:
		if hasattr(self, "_anim_group") and self._anim_group.state() == QParallelAnimationGroup.State.Running:
			self._anim_group.stop()
		self._drag_btn = e.button()
		self._drag_pos = e.position()
		self._drag_az, self._drag_el = self._az, self._el
		self._drag_px, self._drag_py = self._pan_x, self._pan_y
		self._drag_moved = False

	def mouseMoveEvent(self, e) -> None:
		if self._drag_pos is None:
			return
		dp = e.position() - self._drag_pos
		if dp.manhattanLength() > 4:
			self._drag_moved = True
		if self._drag_btn == Qt.MouseButton.LeftButton:
			self._az = self._drag_az + dp.x() * 0.5
			self._el = max(-89.0, min(89.0, self._drag_el - dp.y() * 0.5))
		elif self._drag_btn == Qt.MouseButton.MiddleButton:
			self._pan_x = self._drag_px + dp.x()
			self._pan_y = self._drag_py + dp.y()
		self.update()

	def mouseReleaseEvent(self, e) -> None:
		if (not self._drag_moved
				and e.button() == Qt.MouseButton.LeftButton
				and self._hit_polys):
			pt = e.position()
			for cell2d, poly in self._hit_polys:
				if poly.containsPoint(pt, Qt.FillRule.WindingFill):
					self.cell_clicked.emit(cell2d)
					break
		self._drag_pos = None
		self._drag_btn = None
		self._drag_moved = False

	def wheelEvent(self, e) -> None:
		if hasattr(self, "_anim_group") and self._anim_group.state() == QParallelAnimationGroup.State.Running:
			self._anim_group.stop()
		fac = 1.12 if e.angleDelta().y() > 0 else 1 / 1.12
		self._zoom = max(0.05, min(20.0, self._zoom * fac))
		self.update()

	def mouseDoubleClickEvent(self, e) -> None:
		self.reset_view()

	def _rotate(self, x: float, y: float,
				z: float) -> tuple[float, float, float]:
		az = math.radians(self._az)
		el = math.radians(self._el)
		x1 =  math.cos(az) * x + math.sin(az) * z
		z1 = -math.sin(az) * x + math.cos(az) * z
		y2 =  math.cos(el) * y - math.sin(el) * z1
		z2 =  math.sin(el) * y + math.cos(el) * z1
		return x1, y2, z2

	def paintEvent(self, event) -> None:
		p = QPainter(self)
		p.setRenderHint(QPainter.RenderHint.Antialiasing)
		p.fillRect(self.rect(), QColor("#f1f5f9"))

		W, H = self.width(), self.height()

		if self._nx == 0:
			p.setFont(QFont("Segoe UI", 11))
			p.setPen(QColor("#94a3b8"))
			p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
					   "Tidak ada data spesifikasi grid")
			p.end()
			return

		nx, ny, nz = self._nx, self._ny, self._nz
		dim = max(nx, ny, nz)
		cam = dim * 2.5 + 3.0
		base_scale = min(W, H) * 0.30 * self._zoom / (max(dim, 1) + 0.5)
		h = 0.46  # cube half-size

		ox = (nx - 1) * 0.5
		oy = (ny - 1) * 0.5
		oz = (nz - 1) * 0.5

		def proj(rx: float, ry: float, rz: float) -> tuple[QPointF, float]:
			dz = cam - rz
			if dz < 0.01:
				dz = 0.01
			sc = base_scale * cam / dz
			return (QPointF(W / 2 + self._pan_x + sc * rx,
							H / 2 + self._pan_y - sc * ry), dz)

		cell_centres: dict[int, QPointF] = {}
		face_list: list[dict] = []
		for iz in range(nz):
			for iy in range(ny):
				for ix in range(nx):
					cell2d = iy * nx + ix + 1
					cell3d = iz * nx * ny + iy * nx + ix + 1
					mode   = self._cell_modes.get(cell2d, "normal")

					cx = ix - ox
					cy = -(iy - oy)
					cz = iz - oz

					rc = self._rotate(cx, cy, cz)
					centre_pt, _ = proj(*rc)
					cell_centres[cell3d] = centre_pt

					verts = [
						(cx - h, cy - h, cz - h), (cx + h, cy - h, cz - h),
						(cx + h, cy + h, cz - h), (cx - h, cy + h, cz - h),
						(cx - h, cy - h, cz + h), (cx + h, cy - h, cz + h),
						(cx + h, cy + h, cz + h), (cx - h, cy + h, cz + h),
					]
					rverts = [self._rotate(*v) for v in verts]

					for (fnx, fny, fnz), vi_list, bri in self._FACES:
						_rnx, _rny, rnz = self._rotate(fnx, fny, fnz)
						if rnz <= 0.0:
							continue
						pts_dz = [proj(*rverts[i]) for i in vi_list]
						pts    = [pd[0] for pd in pts_dz]
						depth  = sum(pd[1] for pd in pts_dz) / len(pts_dz)
						face_list.append({
							"depth":  depth,
							"pts":    pts,
							"mode":   mode,
							"bri":    bri,
							"is_top": fny > 0.85,
							"label":  str(cell3d),
							"cell2d": cell2d,
						})

		face_list.sort(key=lambda f: -f["depth"])

		_front: dict[int, tuple[float, QPolygonF]] = {}
		for face in face_list:
			cid = face["cell2d"]
			if cid not in _front or face["depth"] < _front[cid][0]:
				_front[cid] = (face["depth"], QPolygonF(face["pts"]))
		self._hit_polys = [(cid, poly) for cid, (_, poly) in _front.items()]

		p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
		sel = self._selected_cell if hasattr(self, "_selected_cell") else None
		for iz in range(nz):
			for iy in range(ny):
				for ix in range(nx):
					c3d = iz * nx * ny + iy * nx + ix + 1
					c2d = iy * nx + ix + 1
					is_sel = (c2d == sel)
					for dix, diy, diz in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
						nx2, ny2, nz2 = ix + dix, iy + diy, iz + diz
						if 0 <= nx2 < nx and 0 <= ny2 < ny and 0 <= nz2 < nz:
							n3d = nz2 * nx * ny + ny2 * nx + nx2 + 1
							n2d = ny2 * nx + nx2 + 1
							nb_sel = (n2d == sel)
							pa = cell_centres.get(c3d)
							pb = cell_centres.get(n3d)
							if pa and pb:
								if is_sel or nb_sel:
									p.setPen(QPen(QColor("#08b4d8"), 2.5))
								else:
									p.setPen(QPen(QColor("#94a3b860"), 1))
								p.drawLine(pa, pb)
		p.setRenderHint(QPainter.RenderHint.Antialiasing)

		lbl_fsize = max(5, min(22, int(base_scale * 0.55)))
		lbl_font  = QFont("Segoe UI Variable Text", lbl_fsize)
		lbl_font.setBold(True)

		for face in face_list:
			base_rgb, bdr_rgb = self._COLORS.get(face["mode"],
												  self._COLORS["normal"])
			bri = face["bri"]

			def dk(c: int) -> int:
				return max(0, min(255, int(c * bri)))

			fill = QColor(dk(base_rgb[0]), dk(base_rgb[1]), dk(base_rgb[2]))
			bord = QColor(dk(bdr_rgb[0]),  dk(bdr_rgb[1]),  dk(bdr_rgb[2]))

			p.setBrush(QBrush(fill))
			p.setPen(QPen(bord, 1.2))
			p.drawPolygon(QPolygonF(face["pts"]))

			if face["is_top"] and lbl_fsize >= 6:
				xs   = [pt.x() for pt in face["pts"]]
				ys   = [pt.y() for pt in face["pts"]]
				cx_f = sum(xs) / len(xs)
				cy_f = sum(ys) / len(ys)
				tsz  = max(10, min(60, int(base_scale * 0.9)))
				tr   = QRectF(cx_f - tsz / 2, cy_f - tsz / 2, tsz, tsz)
				br   = (0.299 * base_rgb[0] + 0.587 * base_rgb[1]
						+ 0.114 * base_rgb[2])
				tc = (QColor("#1e3a5f") if br * bri > 110
						else QColor("#f8fafc"))
				p.setFont(lbl_font)
				p.setPen(tc)
				p.drawText(tr, Qt.AlignmentFlag.AlignCenter, face["label"])

		self._draw_legend(p)
		self._draw_hint(p, W, H)
		p.end()

	def _draw_legend(self, p: QPainter) -> None:
		entries = [
			("Normal",   "normal"),
			("SIM",      "symmetric"),
			("WELL",     "well"),
			("Selected", "selected"),
		]
		x0, y0 = 12, 12
		p.setFont(QFont("Segoe UI", 8))
		for lbl, mode in entries:
			base_rgb, bdr_rgb = self._COLORS.get(mode, self._COLORS["normal"])
			p.setBrush(QBrush(QColor(*base_rgb)))
			p.setPen(QPen(QColor(*bdr_rgb), 1.5))
			p.drawRoundedRect(QRectF(x0, y0, 14, 14), 3, 3)
			p.setPen(QColor("#475569"))
			p.drawText(QRectF(x0 + 18, y0, 80, 14),
					   Qt.AlignmentFlag.AlignVCenter, lbl)
			y0 += 20

	def _draw_hint(self, p: QPainter, W: int, H: int) -> None:
		p.setFont(QFont("Segoe UI", 7))
		p.setPen(QColor("#94a3b8"))
		p.drawText(
			QRectF(8, H - 16, W - 16, 16),
			Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
			"Drag kiri: putar  •  Scroll: zoom  •  Drag tengah: geser"
			"  •  Klik ganda: reset",
		)


class Connectivity3DPage(QWidget):
	def __init__(self) -> None:
		super().__init__()
		self.project_config: ProjectConfig | None = None
		self._selected_cell: int | None = None
		self._well_cell: int = 1
		self._table_collapsed = False
		self._saved_table_width = 380

		root = QVBoxLayout(self)
		root.setSpacing(0)
		root.setContentsMargins(0, 0, 0, 0)

		# ── Splitter Layout (Side-by-Side) ───────────────────────────────────
		self.splitter = QSplitter(Qt.Orientation.Horizontal)
		self.splitter.setObjectName("mainSplitter")
		self.splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 1px; width: 1px; }")

		# Left Panel: 3D Visualization + Toolbar
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		left_layout.setContentsMargins(0, 0, 0, 0)
		left_layout.setSpacing(0)

		# ── Toolbar Utama (Di dalam Left Panel) ─────────────────────────────────
		toolbar = QWidget()
		toolbar.setObjectName("resultToolbar")
		toolbar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #cbd5e1;")
		tbar = QHBoxLayout(toolbar)
		tbar.setContentsMargins(16, 8, 16, 8)
		tbar.setSpacing(14)

		# Title
		title_lbl = QLabel("Connection 3D")
		title_lbl.setObjectName("pageTitle")
		title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #0891b2;")
		tbar.addWidget(title_lbl)

		tbar.addStretch(1)

		# Status Chip (2/3 width placeholder layout)
		self._conn_status = QLabel("Grid belum dikonfigurasi.")
		self._conn_status.setObjectName("resultStatusLine")
		self._conn_status.setStyleSheet("""
			background-color: #ecfeff;
			color: #0891b2;
			border: 1px solid #bae6fd;
			border-radius: 8px;
			padding: 6px 14px;
			font-size: 9pt;
			font-weight: 600;
		""")
		tbar.addWidget(self._conn_status)

		# Actions: Reset view and Expand/Collapse Table
		btn_reset = QPushButton("  ↺  Reset View")
		btn_reset.setStyleSheet("""
			QPushButton {
				background-color: #ffffff;
				color: #475569;
				border: 1px solid #cbd5e1;
				border-radius: 6px;
				padding: 5px 12px;
				font-size: 9pt;
				font-weight: 600;
			}
			QPushButton:hover {
				background-color: #f8fafc;
				border-color: #0891b2;
				color: #0891b2;
			}
		""")
		btn_reset.clicked.connect(self._conn3d_reset_view)
		tbar.addWidget(btn_reset)

		self.btn_toggle_table = QPushButton("▶")
		self.btn_toggle_table.setFixedSize(34, 34)
		self.btn_toggle_table.setToolTip("Hide Details")
		self.btn_toggle_table.setStyleSheet("""
			QPushButton {
				background-color: #ffffff;
				color: #475569;
				border: 1px solid #cbd5e1;
				border-radius: 6px;
				font-size: 11pt;
				font-weight: bold;
				padding: 0px;
			}
			QPushButton:hover {
				background-color: #f8fafc;
				border-color: #0891b2;
				color: #0891b2;
			}
		""")
		self.btn_toggle_table.clicked.connect(self._toggle_table_panel)
		tbar.addWidget(self.btn_toggle_table)

		left_layout.addWidget(toolbar)

		# Left Content: 3D Visualization Canvas (dengan margins asli)
		left_content_container = QWidget()
		left_content_layout = QVBoxLayout(left_content_container)
		left_content_layout.setContentsMargins(12, 12, 6, 12)
		left_content_layout.setSpacing(0)

		self._conn3d = _Connectivity3DWidget()
		self._conn3d.cell_clicked.connect(self._on_conn3d_cell_clicked)
		left_content_layout.addWidget(self._conn3d, 1)

		left_layout.addWidget(left_content_container, 1)

		# Right Panel: Connection Details Card Panel
		self.right_panel = QWidget()
		self.right_panel.setStyleSheet("background-color: #f8fafc;")
		right_layout = QVBoxLayout(self.right_panel)
		right_layout.setContentsMargins(0, 0, 0, 0)
		right_layout.setSpacing(0)

		# Right Header (Symmetrical to Left Toolbar)
		right_header = QWidget()
		right_header.setObjectName("rightHeader")
		right_header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #cbd5e1;")
		right_hbar = QHBoxLayout(right_header)
		right_hbar.setContentsMargins(16, 8, 16, 8)
		right_hbar.setSpacing(10)

		# Details Group Label
		table_label = QLabel("Selected Cell Connections")
		table_label.setStyleSheet("font-size: 11pt; font-weight: 800; color: #0f172a; letter-spacing: 0.5px;")
		right_hbar.addWidget(table_label)
		right_hbar.addStretch(1)

		right_layout.addWidget(right_header)

		# Right Content Container (dengan margins asli)
		right_content_container = QWidget()
		right_content_layout = QVBoxLayout(right_content_container)
		right_content_layout.setContentsMargins(12, 12, 12, 0)
		right_content_layout.setSpacing(10)

		# Scroll Area for connection cards
		self.scroll_area = QScrollArea()
		self.scroll_area.setWidgetResizable(True)
		self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
		self.scroll_area.setStyleSheet("background-color: transparent;")
		
		self.scroll_content = QWidget()
		self.scroll_content.setStyleSheet("background-color: transparent;")
		self.scroll_layout = QVBoxLayout(self.scroll_content)
		self.scroll_layout.setContentsMargins(0, 0, 0, 0)
		self.scroll_layout.setSpacing(10)
		self.scroll_layout.addStretch(1)
		
		self.scroll_area.setWidget(self.scroll_content)
		right_content_layout.addWidget(self.scroll_area, stretch=1)

		right_layout.addWidget(right_content_container, stretch=1)

		# Premium Controls Container in the Bottom Right
		bottom_controls = QWidget()
		bottom_controls.setStyleSheet("background-color: #ffffff; border-top: 1px solid #cbd5e1; border-top-left-radius: 12px; border-top-right-radius: 12px;")
		bottom_layout = QVBoxLayout(bottom_controls)
		bottom_layout.setContentsMargins(16, 12, 16, 12)
		bottom_layout.setSpacing(6)

		model_label = QLabel("CONNECTIVITY MODEL")
		model_label.setStyleSheet("font-size: 7.5pt; font-weight: 800; color: #64748b; letter-spacing: 1.2px;")
		bottom_layout.addWidget(model_label)

		# Segmented buttons layout (large size buttons)
		seg_widget = QWidget()
		seg_layout = QHBoxLayout(seg_widget)
		seg_layout.setContentsMargins(0, 0, 0, 0)
		seg_layout.setSpacing(0)

		self.btn_5p = QPushButton("5 Points")
		self.btn_9p = QPushButton("9 Points")
		self.btn_11p = QPushButton("11 Points")
		for btn in (self.btn_5p, self.btn_9p, self.btn_11p):
			btn.setCheckable(True)
			seg_layout.addWidget(btn)

		self.btn_group = QButtonGroup(self)
		self.btn_group.addButton(self.btn_5p)
		self.btn_group.addButton(self.btn_9p)
		self.btn_group.addButton(self.btn_11p)
		self.btn_group.setExclusive(True)
		self.btn_5p.setChecked(True)

		large_btn_style = """
		QPushButton {
			background-color: #f8fafc;
			color: #475569;
			border: 1.5px solid #cbd5e1;
			padding: 10px 24px;
			font-size: 10pt;
			font-weight: 700;
			min-height: 40px;
			margin: 0px;
		}
		QPushButton:hover {
			background-color: #f1f5f9;
			color: #0f172a;
			border-color: #94a3b8;
		}
		QPushButton:checked {
			background-color: #0891b2;
			color: #ffffff;
			border-color: #0891b2;
		}
		"""
		self.btn_5p.setStyleSheet(large_btn_style + """
			QPushButton {
				border-top-left-radius: 8px;
				border-bottom-left-radius: 8px;
				border-top-right-radius: 0px;
				border-bottom-right-radius: 0px;
				margin-right: -1px;
			}
		""")
		self.btn_9p.setStyleSheet(large_btn_style + """
			QPushButton {
				border-radius: 0px;
				margin-right: -1px;
			}
		""")
		self.btn_11p.setStyleSheet(large_btn_style + """
			QPushButton {
				border-top-right-radius: 8px;
				border-bottom-right-radius: 8px;
				border-top-left-radius: 0px;
				border-bottom-left-radius: 0px;
				margin-right: 0px;
			}
		""")

		bottom_layout.addWidget(seg_widget)
		right_layout.addWidget(bottom_controls)

		self.splitter.addWidget(left_panel)
		self.splitter.addWidget(self.right_panel)
		
		# Set initial sizes
		self.splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 1px; width: 1px; }")
		self.splitter.setStretchFactor(0, 3)
		self.splitter.setStretchFactor(1, 2)
		self.splitter.setSizes([620, 380])

		root.addWidget(self.splitter, stretch=1)

	def _toggle_table_panel(self) -> None:
		"""Collapse or expand the right connection details panel smoothly."""
		sizes = self.splitter.sizes()
		if len(sizes) < 2:
			return

		if hasattr(self, "_splitter_animation") and self._splitter_animation.state() == QVariantAnimation.State.Running:
			self._splitter_animation.stop()

		self._table_collapsed = not self._table_collapsed

		# Capture current sizes and target width
		total_w = sizes[0] + sizes[1]
		if self._table_collapsed:
			self._saved_table_width = sizes[1] if sizes[1] > 0 else 380
			start_val = sizes[1]
			end_val = 0
			self.btn_toggle_table.setText("◀")
			self.btn_toggle_table.setToolTip("Show Details")
		else:
			start_val = sizes[1]
			end_val = getattr(self, "_saved_table_width", 380)
			if end_val <= 0:
				end_val = 380
			self.btn_toggle_table.setText("▶")
			self.btn_toggle_table.setToolTip("Hide Details")

		self._splitter_animation = QVariantAnimation(self)
		self._splitter_animation.setDuration(300)
		self._splitter_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
		self._splitter_animation.setStartValue(start_val)
		self._splitter_animation.setEndValue(end_val)
		
		# Animate the splitter width values
		self._splitter_animation.valueChanged.connect(lambda val: self.splitter.setSizes([total_w - val, val]))
		self._splitter_animation.start()

	def _on_conn3d_cell_clicked(self, cell2d: int) -> None:
		self._selected_cell = cell2d
		self._refresh_view()

	def _conn3d_reset_view(self) -> None:
		self._conn3d.reset_view()

	def set_project(self, project_config: ProjectConfig) -> None:
		self.project_config = project_config
		
		# Update grid bounds for the 3D viewer
		gs = project_config.grid_spec
		self._conn3d._nx = gs.nx
		self._conn3d._ny = gs.ny
		self._conn3d._nz = getattr(gs, "nz", 1)
		
		self._refresh_view()

	def _get_cell_coords(self, cell_id: int, spec) -> tuple[int, int, int]:
		plane_size = spec.nx * spec.ny
		if plane_size <= 0:
			return 0, 0, 0
		k = cell_id // plane_size
		rem = cell_id % plane_size
		j = rem // spec.nx
		i = rem % spec.nx
		return i, j, k

	def _refresh_view(self) -> None:
		if self.project_config is None:
			return
		gs = self.project_config.grid_spec
		nx = gs.nx
		ny = gs.ny
		nz = getattr(gs, "nz", 1)

		# Build cell connections details list dynamically
		try:
			grid_model = build_grid(self.project_config)
			update_grid_transmissibility(grid_model)
			connections = grid_model.connections
		except Exception:
			connections = []

		# Rebuild scroll area content
		while self.scroll_layout.count() > 1:  # Keep the stretch at the bottom
			child = self.scroll_layout.takeAt(0)
			if child.widget():
				child.widget().deleteLater()

		# Setup dynamic connection modes for the 3D widget
		sym_set: set[int] = (
			set(_symmetric_cells(self._selected_cell, self._well_cell, nx, ny))
			if self._selected_cell is not None
			else set()
		)

		modes: dict[int, str] = {}
		for cell2d in range(1, nx * ny + 1):
			if cell2d == self._well_cell:
				modes[cell2d] = "well"
			elif cell2d == self._selected_cell:
				modes[cell2d] = "selected"
			elif cell2d in sym_set:
				modes[cell2d] = "symmetric"
			else:
				modes[cell2d] = "normal"

		self._conn3d.set_grid(nx, ny, nz, modes, self._selected_cell)
		
		# Update status bar: showing 2/3 of toolbar width as requested
		n_total = nx * ny * nz
		sel_txt = f"  ·  Sel: {self._selected_cell}" if self._selected_cell else ""
		self._conn_status.setText(
			f"Grid {nx}×{ny}×{nz} ({n_total} sel)  ·  {len(connections)} total koneksi{sel_txt}"
		)

		if self._selected_cell is None:
			# Show friendly placeholder when no cell is selected
			placeholder = QLabel("Pilih sel pada model 3D di sebelah kiri untuk melihat detail koneksi.")
			placeholder.setWordWrap(True)
			placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
			placeholder.setStyleSheet("color: #64748b; font-size: 10pt; font-style: italic; padding: 40px;")
			self.scroll_layout.insertWidget(0, placeholder)
		else:
			# Filter and show connection cards for the selected cell
			selected_cell_0 = self._selected_cell - 1
			cell_connections = [
				c for c in connections
				if c.from_cell_id == selected_cell_0 or c.to_cell_id == selected_cell_0
			]

			if not cell_connections:
				no_conn_lbl = QLabel(f"Tidak ada koneksi untuk Cell {self._selected_cell}.")
				no_conn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
				no_conn_lbl.setStyleSheet("color: #64748b; font-size: 10pt; font-style: italic; padding: 20px;")
				self.scroll_layout.insertWidget(0, no_conn_lbl)
			else:
				for idx, conn in enumerate(cell_connections):
					neighbor_id = conn.to_cell_id if conn.from_cell_id == selected_cell_0 else conn.from_cell_id
					n_i, n_j, n_k = self._get_cell_coords(neighbor_id, gs)
					
					# Create connection card
					card = QFrame()
					card.setObjectName("connectionCard")
					card_style = """
					QFrame#connectionCard {
						background-color: #ffffff;
						border: 1.5px solid #cbd5e1;
						border-radius: 8px;
					}
					QFrame#connectionCard:hover {
						border-color: #0891b2;
						background-color: #f8fafc;
					}
					"""
					card.setStyleSheet(card_style)
					
					card_layout = QVBoxLayout(card)
					card_layout.setContentsMargins(12, 12, 12, 12)
					card_layout.setSpacing(10)
					
					# Card title
					card_title = QLabel(f"Koneksi ke Cell {neighbor_id} ({n_i}, {n_j}, {n_k})")
					card_title.setStyleSheet("font-size: 9.5pt; font-weight: 800; color: #0891b2;")
					card_layout.addWidget(card_title)
					
					# Grid layout for properties
					prop_grid = QWidget()
					grid_lay = QGridLayout(prop_grid)
					grid_lay.setContentsMargins(0, 0, 0, 0)
					grid_lay.setSpacing(6)
					
					# Style helpers
					k_style = "font-size: 8.5pt; font-weight: 700; color: #475569;"
					v_style = "font-size: 9pt; font-weight: 800; color: #0f172a;"
					
					# 1. Direction
					lbl_dir_k = QLabel("Direction:")
					lbl_dir_k.setStyleSheet(k_style)
					lbl_dir_v = QLabel(conn.direction)
					lbl_dir_v.setStyleSheet(v_style)
					grid_lay.addWidget(lbl_dir_k, 0, 0)
					grid_lay.addWidget(lbl_dir_v, 0, 1)
					
					# 2. Area
					lbl_area_k = QLabel("Area:")
					lbl_area_k.setStyleSheet(k_style)
					lbl_area_v = QLabel(f"{conn.area:,.1f} ft²")
					lbl_area_v.setStyleSheet(v_style)
					grid_lay.addWidget(lbl_area_k, 0, 2)
					grid_lay.addWidget(lbl_area_v, 0, 3)
					
					# 3. Distance
					lbl_dist_k = QLabel("Distance:")
					lbl_dist_k.setStyleSheet(k_style)
					lbl_dist_v = QLabel(f"{conn.distance:,.1f} ft")
					lbl_dist_v.setStyleSheet(v_style)
					grid_lay.addWidget(lbl_dist_k, 1, 0)
					grid_lay.addWidget(lbl_dist_v, 1, 1)
					
					# 4. Transmissibility
					lbl_trans_k = QLabel("Transmissibility:")
					lbl_trans_k.setStyleSheet(k_style)
					lbl_trans_v = QLabel(f"{conn.transmissibility:,.4f}")
					lbl_trans_v.setStyleSheet(v_style)
					grid_lay.addWidget(lbl_trans_k, 1, 2)
					grid_lay.addWidget(lbl_trans_v, 1, 3)
					
					card_layout.addWidget(prop_grid)
					self.scroll_layout.insertWidget(idx, card)

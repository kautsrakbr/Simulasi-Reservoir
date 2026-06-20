from __future__ import annotations

import math
from PySide6.QtCore import Qt, QLineF, QPointF, Signal, QRectF, QSize, Property, QVariantAnimation, QParallelAnimationGroup, QPropertyAnimation, QEasingCurve, QTimer
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
from engine.physics.transmissibility import compute_transmissibility, update_grid_transmissibility
from engine.common.constants import TRANSMISSIBILITY_UNIT_FACTOR



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
		"connected": ((209, 250, 229), ( 16, 185, 129)),
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
		self._top_face_centres: dict[int, QPointF] = {}
		self._last_base_scale: float = 1.0
		self._show_top_layer: bool = False
		self._focus_mode = False
		self._flat_mode = False
		self._flat_x0 = self._flat_y0 = self._flat_cs = 0.0
		self._update_pending = False
		self._throttle_timer = QTimer(self)
		self._throttle_timer.setInterval(14)  # ~70fps cap
		self._throttle_timer.setSingleShot(True)
		self._throttle_timer.timeout.connect(self._flush_update)
		self.setMinimumSize(300, 260)
		self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

	def _schedule_update(self) -> None:
		"""Rate-limit repaints to ~70fps so high mouse poll rates don't pile up."""
		if not self._throttle_timer.isActive():
			self._throttle_timer.start()

	def _flush_update(self) -> None:
		self.update()

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

	def set_focus_mode(self, enabled: bool) -> None:
		self._focus_mode = enabled
		self.update()

	def focus_on_cell(self, cell3d: int) -> None:
		if self._flat_mode:
			plane = self._nx * self._ny
			c0 = (cell3d - 1) % plane
			ix = c0 % self._nx
			iy = c0 // self._nx
			pt = QPointF(
				self._flat_x0 + (ix + 0.5) * self._flat_cs,
				self._flat_y0 + (iy + 0.5) * self._flat_cs,
			)
		else:
			if cell3d not in self._top_face_centres:
				return
			pt = self._top_face_centres[cell3d]
		W, H = self.width(), self.height()
		
		target_px = self._pan_x - (pt.x() - W / 2)
		target_py = self._pan_y - (pt.y() - H / 2)

		if hasattr(self, "_focus_anim") and self._focus_anim.state() == QParallelAnimationGroup.State.Running:
			self._focus_anim.stop()

		self.anim_px = QPropertyAnimation(self, b"pan_x", self)
		self.anim_px.setDuration(400)
		self.anim_px.setStartValue(self._pan_x)
		self.anim_px.setEndValue(target_px)
		self.anim_px.setEasingCurve(QEasingCurve.Type.OutCubic)

		self.anim_py = QPropertyAnimation(self, b"pan_y", self)
		self.anim_py.setDuration(400)
		self.anim_py.setStartValue(self._pan_y)
		self.anim_py.setEndValue(target_py)
		self.anim_py.setEasingCurve(QEasingCurve.Type.OutCubic)

		self._focus_anim = QParallelAnimationGroup(self)
		self._focus_anim.addAnimation(self.anim_px)
		self._focus_anim.addAnimation(self.anim_py)
		self._focus_anim.start()

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

	def set_show_top_layer(self, show: bool) -> None:
		self._show_top_layer = show
		self.update()

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
			if self._flat_mode:
				self._pan_x = self._drag_px + dp.x()
				self._pan_y = self._drag_py + dp.y()
			else:
				self._az = self._drag_az + dp.x() * 0.5
				self._el = max(-89.0, min(89.0, self._drag_el - dp.y() * 0.5))
		elif self._drag_btn == Qt.MouseButton.MiddleButton:
			self._pan_x = self._drag_px + dp.x()
			self._pan_y = self._drag_py + dp.y()
		self._schedule_update()

	def mouseReleaseEvent(self, e) -> None:
		if not self._drag_moved and e.button() == Qt.MouseButton.LeftButton:
			pt = e.position()
			cell = None
			if self._flat_mode:
				cell = self._flat_hit_test(pt)
			elif self._hit_polys:
				for c, poly in self._hit_polys:
					if poly.containsPoint(pt, Qt.FillRule.WindingFill):
						cell = c
						break
			if cell is not None:
				self.cell_clicked.emit(cell)
				self.focus_on_cell(cell)
		self._drag_pos = None
		self._drag_btn = None
		self._drag_moved = False

	def _flat_hit_test(self, pt: QPointF) -> int | None:
		if self._flat_cs <= 0:
			return None
		ix = int((pt.x() - self._flat_x0) / self._flat_cs)
		iy = int((pt.y() - self._flat_y0) / self._flat_cs)
		if 0 <= ix < self._nx and 0 <= iy < self._ny:
			return (self._nz - 1) * self._nx * self._ny + iy * self._nx + ix + 1
		return None

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

	# Grid larger than this (cells in XY plane) switches to 2D flat rendering
	_FLAT_THRESHOLD = 3_000

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
		self._flat_mode = nx * ny * nz > self._FLAT_THRESHOLD

		if self._flat_mode:
			self._paint_flat(p, W, H, nx, ny, nz)
		else:
			self._paint_3d(p, W, H, nx, ny, nz)

		self._draw_overlay(p)
		self._draw_legend(p)
		self._draw_hint(p, W, H)
		p.end()

	def _paint_flat(self, p: QPainter, W: int, H: int,
					nx: int, ny: int, nz: int) -> None:
		"""Fast 2D top-down rendering for large grids."""
		margin = 24
		cs = max(0.5, min(
			(W - 2 * margin) * self._zoom / nx,
			(H - 2 * margin) * self._zoom / ny,
		))
		grid_w = cs * nx
		grid_h = cs * ny
		x0 = (W - grid_w) / 2 + self._pan_x
		y0 = (H - grid_h) / 2 + self._pan_y

		self._flat_x0, self._flat_y0, self._flat_cs = x0, y0, cs
		self._last_base_scale = cs

		# Viewport-clipped cell index ranges (avoids iterating off-screen cells)
		ix_lo = max(0, int((0.0 - x0) / cs))
		ix_hi = min(nx - 1, int((W - x0) / cs) + 1)
		iy_lo = max(0, int((0.0 - y0) / cs))
		iy_hi = min(ny - 1, int((H - y0) / cs) + 1)

		# Fill grid area with normal color (single rect — instant even for 999×999)
		n_rgb, n_bdr = self._COLORS["normal"]
		p.setBrush(QBrush(QColor(*n_rgb)))
		p.setPen(Qt.PenStyle.NoPen)
		p.drawRect(QRectF(x0, y0, grid_w, grid_h))

		# Draw only non-normal cells (sparse — usually < 100 cells)
		plane = nx * ny
		for cell3d, mode in self._cell_modes.items():
			if mode == "normal":
				continue
			c0 = (cell3d - 1) % plane
			ix, iy = c0 % nx, c0 // nx
			base_rgb, _ = self._COLORS.get(mode, self._COLORS["normal"])
			p.setBrush(QBrush(QColor(*base_rgb)))
			p.setPen(Qt.PenStyle.NoPen)
			p.drawRect(QRectF(x0 + ix * cs, y0 + iy * cs, cs, cs))

		# Grid lines — skip sub-pixel; cull to viewport; batch into one drawLines() call
		if cs >= 1.5:
			pen_w = max(0.3, cs * 0.04)
			p.setBrush(Qt.BrushStyle.NoBrush)
			p.setPen(QPen(QColor(*n_bdr), pen_w))
			clip_y0 = max(y0, 0.0)
			clip_y1 = min(y0 + grid_h, float(H))
			clip_x0 = max(x0, 0.0)
			clip_x1 = min(x0 + grid_w, float(W))
			lines: list[QLineF] = []
			for ix in range(ix_lo, ix_hi + 2):
				lx = x0 + ix * cs
				lines.append(QLineF(lx, clip_y0, lx, clip_y1))
			for iy in range(iy_lo, iy_hi + 2):
				ly = y0 + iy * cs
				lines.append(QLineF(clip_x0, ly, clip_x1, ly))
			if lines:
				p.drawLines(lines)

		# Cell labels — only when cells are large enough; cull to visible cells only
		if cs >= 20:
			chip_font = QFont("Segoe UI", max(5, int(cs * 0.22)))
			chip_font.setBold(True)
			p.setFont(chip_font)
			for iy in range(iy_lo, iy_hi + 1):
				for ix in range(ix_lo, ix_hi + 1):
					cell3d = (nz - 1) * plane + iy * nx + ix + 1
					mode = self._cell_modes.get(cell3d, "normal")
					base_rgb, _ = self._COLORS.get(mode, self._COLORS["normal"])
					br = 0.299 * base_rgb[0] + 0.587 * base_rgb[1] + 0.114 * base_rgb[2]
					rx, ry = x0 + ix * cs, y0 + iy * cs
					p.setPen(QColor("#0f172a") if br > 150 else QColor("#ffffff"))
					p.drawText(QRectF(rx, ry, cs, cs), Qt.AlignmentFlag.AlignCenter, str(cell3d))

		# Populate _top_face_centres for overlay use (sparse — non-normal + well cells only)
		self._top_face_centres = {}
		for cell3d, mode in self._cell_modes.items():
			if mode != "normal":
				c0 = (cell3d - 1) % plane
				ix, iy = c0 % nx, c0 // nx
				self._top_face_centres[cell3d] = QPointF(
					x0 + (ix + 0.5) * cs, y0 + (iy + 0.5) * cs
				)
		for cell2d_val in getattr(self, "_well_info", {}):
			for _iz in range(nz - 1, -1, -1):
				c3 = _iz * plane + cell2d_val
				if c3 not in self._top_face_centres:
					c0 = cell2d_val - 1
					ix, iy = c0 % nx, c0 // nx
					self._top_face_centres[c3] = QPointF(
						x0 + (ix + 0.5) * cs, y0 + (iy + 0.5) * cs
					)
				break

		self._hit_polys = []  # unused in flat mode

	def _paint_3d(self, p: QPainter, W: int, H: int,
				  nx: int, ny: int, nz: int) -> None:
		"""Full 3D cube rendering for smaller grids."""
		dim = max(nx, ny, nz)
		cam = dim * 2.5 + 3.0
		base_scale = min(W, H) * 0.30 * self._zoom / (max(dim, 1) + 0.5)
		h = 0.46

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

		face_list: list[dict] = []
		for iz in range(nz):
			for iy in range(ny):
				for ix in range(nx):
					cell3d = iz * nx * ny + iy * nx + ix + 1
					mode   = self._cell_modes.get(cell3d, "normal")

					if self._focus_mode and self._selected_cell is not None:
						if cell3d != self._selected_cell and mode not in ("connected", "well", "perturbed", "selected"):
							continue

					cx = ix - ox
					cy = iz - oz
					cz = -(iy - oy)

					rverts = [self._rotate(*v) for v in [
						(cx - h, cy - h, cz - h), (cx + h, cy - h, cz - h),
						(cx + h, cy + h, cz - h), (cx - h, cy + h, cz - h),
						(cx - h, cy - h, cz + h), (cx + h, cy - h, cz + h),
						(cx + h, cy + h, cz + h), (cx - h, cy + h, cz + h),
					]]

					for (fnx, fny, fnz), vi_list, bri in self._FACES:
						_rnx, _rny, rnz = self._rotate(fnx, fny, fnz)
						if rnz < 0.0:
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
							"iz":     iz,
							"label":  str(cell3d),
							"cell2d": cell3d,
						})

		face_list.sort(key=lambda f: -f["depth"])

		_front: dict[int, tuple[float, QPolygonF]] = {}
		for face in face_list:
			cid = face["cell2d"]
			if cid not in _front or face["depth"] < _front[cid][0]:
				_front[cid] = (face["depth"], QPolygonF(face["pts"]))
		self._hit_polys = [
			(cid, poly)
			for cid, (depth, poly) in sorted(_front.items(), key=lambda kv: kv[1][0])
		]

		chip_fsize = max(5, min(11, int(base_scale * 0.26)))
		chip_font  = QFont("Segoe UI", chip_fsize)
		chip_font.setBold(True)

		for face in face_list:
			base_rgb, bdr_rgb = self._COLORS.get(face["mode"], self._COLORS["normal"])
			if (self._show_top_layer
					and face.get("is_top")
					and face.get("iz") == nz - 1
					and face["mode"] == "normal"):
				base_rgb = (254, 243, 199)
				bdr_rgb  = (251, 191,  36)
			bri = face["bri"]

			def dk(c: int) -> int:
				return max(0, min(255, int(c * bri)))

			p.setBrush(QBrush(QColor(dk(base_rgb[0]), dk(base_rgb[1]), dk(base_rgb[2]))))
			p.setPen(QPen(QColor(dk(bdr_rgb[0]), dk(bdr_rgb[1]), dk(bdr_rgb[2])), 1.2))
			p.drawPolygon(QPolygonF(face["pts"]))

			if face["is_top"] and chip_fsize >= 5:
				if self._selected_cell is not None and face["cell2d"] != self._selected_cell and face["mode"] != "connected" and face["mode"] != "perturbed":
					continue
				xs   = [pt.x() for pt in face["pts"]]
				ys   = [pt.y() for pt in face["pts"]]
				cx_f = sum(xs) / len(xs)
				cy_f = sum(ys) / len(ys)
				label = face["label"]
				p.setFont(chip_font)
				fm   = p.fontMetrics()
				tw   = fm.horizontalAdvance(label)
				bh   = chip_fsize + 6
				bw   = max(tw + 10, bh)
				bx   = cx_f - bw / 2
				by   = cy_f - bh / 2
				br_lum = (0.299 * base_rgb[0] + 0.587 * base_rgb[1] + 0.114 * base_rgb[2]) * bri
				if br_lum > 130:
					chip_bg  = QColor(30,  41,  59, 130)
					chip_txt = QColor(255, 255, 255, 220)
				else:
					chip_bg  = QColor(255, 255, 255, 130)
					chip_txt = QColor(15,  23,  42, 220)
				p.setBrush(QBrush(chip_bg))
				p.setPen(Qt.PenStyle.NoPen)
				p.drawRoundedRect(QRectF(bx, by, bw, bh), bh / 2, bh / 2)
				p.setPen(chip_txt)
				p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, label)

		self._last_base_scale = base_scale
		self._top_face_centres = {}
		for face in face_list:
			if face["is_top"]:
				cid = face["cell2d"]
				xs = [pt.x() for pt in face["pts"]]
				ys = [pt.y() for pt in face["pts"]]
				self._top_face_centres[cid] = QPointF(sum(xs) / len(xs), sum(ys) / len(ys))

	def _draw_overlay(self, p: QPainter) -> None:
		"""Subclasses override this to draw symbols on top of the cells."""

	def _draw_legend(self, p: QPainter) -> None:
		entries = [
			("Normal",    "normal"),
			("Connected", "connected"),
			("Selected",  "selected"),
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
		if self._flat_mode:
			hint = "Drag: geser  •  Scroll: zoom  •  Klik: pilih sel  •  Klik ganda: reset"
		else:
			hint = "Drag kiri: putar  •  Scroll: zoom  •  Drag tengah: geser  •  Klik ganda: reset"
		p.drawText(
			QRectF(8, H - 16, W - 16, 16),
			Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
			hint,
		)


class Connectivity3DPage(QWidget):
	def __init__(self) -> None:
		super().__init__()
		self.project_config: ProjectConfig | None = None
		self._selected_cell: int | None = None
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

		# Focus mode button
		self.btn_focus = QPushButton("Focus Mode")
		self.btn_focus.setCheckable(True)
		self.btn_focus.setChecked(False)
		self.btn_focus.setCursor(Qt.CursorShape.PointingHandCursor)
		self.btn_focus.setStyleSheet("""
			QPushButton {
				background-color: #ffffff;
				color: #475569;
				border: 1.5px solid #e2e8f0;
				border-radius: 8px;
				padding: 6px 14px;
				font-size: 9pt;
				font-weight: 700;
			}
			QPushButton:hover {
				background-color: #ecfeff;
				border-color: #67e8f9;
				color: #0891b2;
			}
			QPushButton:checked {
				background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
					stop:0 #22d3ee, stop:1 #0891b2);
				border-color: #0891b2;
				color: #ffffff;
				font-weight: 800;
			}
		""")
		self.btn_focus.clicked.connect(self._on_focus_toggle)
		tbar.addWidget(self.btn_focus)

		# Actions: Reset view and Expand/Collapse Table
		btn_reset = QPushButton("↺  Reset View")
		btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
		btn_reset.setStyleSheet("""
			QPushButton {
				background-color: #ffffff;
				color: #475569;
				border: 1.5px solid #e2e8f0;
				border-radius: 8px;
				padding: 6px 14px;
				font-size: 9pt;
				font-weight: 700;
			}
			QPushButton:hover {
				background-color: #ecfeff;
				border-color: #67e8f9;
				color: #0891b2;
			}
		""")
		btn_reset.clicked.connect(self._conn3d_reset_view)
		tbar.addWidget(btn_reset)

		self.btn_toggle_table = QPushButton("▶")
		self.btn_toggle_table.setFixedSize(34, 34)
		self.btn_toggle_table.setToolTip("Hide Details")
		self.btn_toggle_table.setCursor(Qt.CursorShape.PointingHandCursor)
		self.btn_toggle_table.setStyleSheet("""
			QPushButton {
				background-color: #ffffff;
				color: #475569;
				border: 1.5px solid #e2e8f0;
				border-radius: 8px;
				font-size: 11pt;
				font-weight: bold;
				padding: 0px;
			}
			QPushButton:hover {
				background-color: #ecfeff;
				border-color: #67e8f9;
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
		self.scroll_layout.setContentsMargins(8, 8, 8, 8)
		self.scroll_layout.setSpacing(10)
		self.scroll_layout.addStretch(1)
		
		self.scroll_area.setWidget(self.scroll_content)
		right_content_layout.addWidget(self.scroll_area, stretch=1)

		right_layout.addWidget(right_content_container, stretch=1)

		# Premium Controls Container in the Bottom Right
		bottom_controls = QWidget()
		bottom_controls.setObjectName("bottomPanel")
		bottom_controls.setStyleSheet("""
			QWidget#bottomPanel {
				background-color: #ffffff;
				border-top: 1px solid #e2e8f0;
				border-top-left-radius: 14px;
				border-top-right-radius: 14px;
			}
		""")
		bottom_shadow = QGraphicsDropShadowEffect(bottom_controls)
		bottom_shadow.setBlurRadius(24)
		bottom_shadow.setColor(QColor(15, 23, 42, 35))
		bottom_shadow.setOffset(0, -3)
		bottom_controls.setGraphicsEffect(bottom_shadow)

		bottom_layout = QVBoxLayout(bottom_controls)
		bottom_layout.setContentsMargins(16, 16, 16, 16)
		bottom_layout.setSpacing(7)

		model_label = QLabel("CONNECTIVITY MODEL")
		model_label.setStyleSheet("font-size: 7.5pt; font-weight: 800; color: #94a3b8; letter-spacing: 1.2px;")
		bottom_layout.addWidget(model_label)

		# Segmented buttons layout — rounded pill container (matches Well Placement style)
		seg_widget = QWidget()
		seg_widget.setObjectName("segContainer")
		seg_widget.setStyleSheet(
			"QWidget#segContainer { background-color: #eef2f6; border-radius: 10px; }"
		)
		seg_layout = QHBoxLayout(seg_widget)
		seg_layout.setContentsMargins(3, 3, 3, 3)
		seg_layout.setSpacing(2)

		self.btn_5p = QPushButton("5 Points")
		self.btn_9p = QPushButton("9 Points")
		self.btn_11p = QPushButton("11 Points")
		for btn in (self.btn_5p, self.btn_9p, self.btn_11p):
			btn.setCheckable(True)
			btn.setCursor(Qt.CursorShape.PointingHandCursor)
			seg_layout.addWidget(btn)

		self.btn_group = QButtonGroup(self)
		self.btn_group.addButton(self.btn_5p)
		self.btn_group.addButton(self.btn_9p)
		self.btn_group.addButton(self.btn_11p)
		self.btn_group.setExclusive(True)
		self.btn_5p.setChecked(True)

		large_btn_style = """
		QPushButton {
			background-color: transparent;
			color: #64748b;
			border: 1px solid transparent;
			border-radius: 8px;
			padding: 9px 22px;
			font-size: 9.5pt;
			font-weight: 700;
			min-height: 32px;
		}
		QPushButton:hover {
			background-color: #e2e8f0;
			color: #0f172a;
		}
		QPushButton:checked {
			background-color: #ffffff;
			color: #0f172a;
			font-weight: 800;
			border: 1px solid #dbe2ea;
		}
		"""
		for btn in (self.btn_5p, self.btn_9p, self.btn_11p):
			btn.setStyleSheet(large_btn_style)

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

	def _on_focus_toggle(self) -> None:
		self._conn3d.set_focus_mode(self.btn_focus.isChecked())

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

	# Grids larger than this use fast O(1) math instead of full build_grid
	_CONN_BUILD_LIMIT = 30_000

	def set_project(self, project_config: ProjectConfig) -> None:
		self.project_config = project_config
		self._conn_cache: list = []
		self._conn_cache_spec: tuple | None = None

		gs = project_config.grid_spec
		self._conn3d._nx = gs.nx
		self._conn3d._ny = gs.ny
		self._conn3d._nz = getattr(gs, "nz", 1)

		self._refresh_view()

	def _fast_neighbors(self, cell3d: int, nx: int, ny: int, nz: int) -> set[int]:
		"""O(1) Cartesian neighbor lookup — no grid build needed."""
		c0 = cell3d - 1
		plane = nx * ny
		iz = c0 // plane
		iy = (c0 % plane) // nx
		ix = c0 % nx
		nb: set[int] = set()
		if ix > 0:      nb.add(c0 - 1 + 1)
		if ix < nx - 1: nb.add(c0 + 1 + 1)
		if iy > 0:      nb.add(c0 - nx + 1)
		if iy < ny - 1: nb.add(c0 + nx + 1)
		if iz > 0:      nb.add(c0 - plane + 1)
		if iz < nz - 1: nb.add(c0 + plane + 1)
		return nb

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
		n_total = nx * ny * nz

		# ── Connection source: fast math (large) vs cached build_grid (small) ──
		use_fast = n_total > self._CONN_BUILD_LIMIT
		connections: list | None = None
		if not use_fast:
			spec_key = (nx, ny, nz)
			if getattr(self, "_conn_cache_spec", None) != spec_key:
				try:
					grid_model = build_grid(self.project_config)
					update_grid_transmissibility(grid_model)
					self._conn_cache = grid_model.connections
				except Exception:
					self._conn_cache = []
				self._conn_cache_spec = spec_key
			connections = self._conn_cache

		# Rebuild scroll area content
		while self.scroll_layout.count() > 1:
			item = self.scroll_layout.takeAt(0)
			if item is not None:
				w = item.widget()
				if w is not None:
					w.hide()
					w.deleteLater()

		# ── Connected cells set ──
		connected_set: set[int] = set()
		if self._selected_cell is not None:
			if use_fast:
				connected_set = self._fast_neighbors(self._selected_cell, nx, ny, nz)
			elif connections:
				selected_3d_0 = self._selected_cell - 1
				for conn in connections:
					if conn.from_cell_id == selected_3d_0:
						connected_set.add(conn.to_cell_id + 1)
					elif conn.to_cell_id == selected_3d_0:
						connected_set.add(conn.from_cell_id + 1)

		modes: dict[int, str] = {}
		if self._selected_cell is not None:
			modes[self._selected_cell] = "selected"
		for cell3d in connected_set:
			if cell3d != self._selected_cell:
				modes[cell3d] = "connected"

		self._conn3d.set_grid(nx, ny, nz, modes, self._selected_cell)

		# Status bar
		if use_fast:
			n_conn = (nx - 1) * ny * nz + nx * (ny - 1) * nz + nx * ny * (nz - 1)
		else:
			n_conn = len(connections) if connections else 0
		sel_txt = f"  ·  Sel: {self._selected_cell}" if self._selected_cell else ""
		self._conn_status.setText(
			f"Grid {nx}×{ny}×{nz} ({n_total} sel)  ·  {n_conn} total koneksi{sel_txt}"
		)

		if self._selected_cell is None:
			# Placeholder when no cell selected
			ph_outer = QWidget()
			ph_outer.setStyleSheet("background: transparent;")
			ph_outer_lay = QVBoxLayout(ph_outer)
			ph_outer_lay.setContentsMargins(12, 40, 12, 40)
			ph_outer_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

			ph_w = QWidget()
			ph_w.setObjectName("placeholderCard")
			ph_w.setStyleSheet("""
				QWidget#placeholderCard {
					background-color: #ffffff;
					border: 2px dashed #cbd5e1;
					border-radius: 12px;
				}
			""")
			ph_w.setFixedWidth(280)
			ph_lay = QVBoxLayout(ph_w)
			ph_lay.setContentsMargins(20, 28, 20, 28)
			ph_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
			ph_lay.setSpacing(14)

			ph_icon = QLabel("🔌")
			ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
			ph_icon.setStyleSheet("font-size: 26pt; background: transparent;")
			ph_lay.addWidget(ph_icon)

			ph_title = QLabel("Koneksi Sel Grid")
			ph_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
			ph_title.setStyleSheet(
				"font-size: 11pt; font-weight: 800; color: #0891b2; background: transparent;"
			)
			ph_lay.addWidget(ph_title)

			ph_sub = QLabel(
				"Pilih sel pada model 3D di sebelah kiri untuk melihat detail koneksi antarsel."
			)
			ph_sub.setWordWrap(True)
			ph_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
			ph_sub.setStyleSheet("font-size: 8.5pt; color: #64748b; background: transparent; line-height: 1.4;")
			ph_lay.addWidget(ph_sub)

			ph_outer_lay.addWidget(ph_w)
			self.scroll_layout.insertWidget(0, ph_outer)
			self._animate_card(ph_outer, 0)
		else:
			# ── Build connection cards ──
			if use_fast:
				# Compute cards inline from geometry — no full grid needed
				self._build_fast_cards(connected_set, gs, nx)
			else:
				selected_cell_0 = self._selected_cell - 1
				cell_connections = [
					c for c in (connections or [])
					if c.from_cell_id == selected_cell_0 or c.to_cell_id == selected_cell_0
				]
				if not cell_connections:
					no_conn_lbl = QLabel(f"Tidak ada koneksi untuk Cell {self._selected_cell}.")
					no_conn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
					no_conn_lbl.setStyleSheet("color: #64748b; font-size: 10pt; font-style: italic; padding: 20px;")
					self.scroll_layout.insertWidget(0, no_conn_lbl)
					self._animate_card(no_conn_lbl, 0)
				else:
					for idx, conn in enumerate(cell_connections):
						neighbor_id = conn.to_cell_id if conn.from_cell_id == selected_cell_0 else conn.from_cell_id
						n_i, n_j, n_k = self._get_cell_coords(neighbor_id, gs)
						wrapper = self._build_conn_card(neighbor_id, n_i, n_j, n_k,
							conn.direction, conn.area, conn.distance, conn.transmissibility)
						self.scroll_layout.insertWidget(idx, wrapper)
						self._animate_card(wrapper, idx * 80)

	def _build_fast_cards(self, connected_set: set[int], gs, nx: int) -> None:
		"""Build connection cards using inline geometry for large grids (no full build_grid)."""
		plane = nx * gs.ny
		sel_0 = self._selected_cell - 1
		for idx, nb_cell3d in enumerate(sorted(connected_set)):
			nb_0 = nb_cell3d - 1
			diff = nb_0 - sel_0
			if abs(diff) == 1:
				direction = "x+" if diff > 0 else "x-"
				area = gs.dy * gs.dz
				dist = gs.dx
			elif abs(diff) == nx:
				direction = "y+" if diff > 0 else "y-"
				area = gs.dx * gs.dz
				dist = gs.dy
			else:
				direction = "z+" if diff > 0 else "z-"
				area = gs.dx * gs.dy
				dist = gs.dz
			k = 100.0
			trans = compute_transmissibility(k, k, area, dist, TRANSMISSIBILITY_UNIT_FACTOR)
			ni = nb_0 % nx
			nj = (nb_0 % plane) // nx
			nk = nb_0 // plane
			wrapper = self._build_conn_card(nb_cell3d, ni, nj, nk, direction, area, dist, trans)
			self.scroll_layout.insertWidget(idx, wrapper)
			self._animate_card(wrapper, idx * 80)

	def _build_conn_card(self, neighbor_id: int, n_i: int, n_j: int, n_k: int,
						  direction: str, area: float, distance: float, trans: float) -> QWidget:
		"""Build a single connection card widget."""
		wrapper = QWidget()
		wrapper.setStyleSheet("background: transparent;")
		wrapper_lay = QVBoxLayout(wrapper)
		wrapper_lay.setContentsMargins(0, 0, 0, 0)
		wrapper_lay.setSpacing(0)

		card = QFrame()
		card.setObjectName("connectionCard")
		card.setStyleSheet("""
			QFrame#connectionCard { background-color: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 8px; }
			QFrame#connectionCard:hover { border-color: #0891b2; background-color: #f8fafc; }
		""")
		shadow = QGraphicsDropShadowEffect(card)
		shadow.setBlurRadius(10)
		shadow.setColor(QColor(15, 23, 42, 18))
		shadow.setOffset(0, 2)
		card.setGraphicsEffect(shadow)

		card_layout = QVBoxLayout(card)
		card_layout.setContentsMargins(12, 12, 12, 12)
		card_layout.setSpacing(10)

		card_title = QLabel(f"Koneksi ke Cell {neighbor_id} ({n_i}, {n_j}, {n_k})")
		card_title.setStyleSheet("font-size: 9.5pt; font-weight: 800; color: #0891b2;")
		card_layout.addWidget(card_title)

		prop_grid = QWidget()
		grid_lay = QGridLayout(prop_grid)
		grid_lay.setContentsMargins(0, 0, 0, 0)
		grid_lay.setSpacing(6)
		k_style = "font-size: 8.5pt; font-weight: 700; color: #475569;"
		v_style = "font-size: 9pt; font-weight: 800; color: #0f172a;"

		for row, (lbl_k, lbl_v) in enumerate([
			("Direction:", direction),
			("Area:", f"{area:,.1f} ft²"),
			("Distance:", f"{distance:,.1f} ft"),
			("Transmissibility:", f"{trans:,.4f}"),
		]):
			col = (row % 2) * 2
			r = row // 2
			k_lbl = QLabel(lbl_k); k_lbl.setStyleSheet(k_style)
			v_lbl = QLabel(lbl_v); v_lbl.setStyleSheet(v_style)
			grid_lay.addWidget(k_lbl, r, col)
			grid_lay.addWidget(v_lbl, r, col + 1)

		card_layout.addWidget(prop_grid)
		wrapper_lay.addWidget(card)
		return wrapper

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
	QButtonGroup,
	QFrame,
	QGraphicsOpacityEffect,
	QHBoxLayout,
	QLabel,
	QPushButton,
	QScrollArea,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import MethodConfig, ProjectConfig


_METHOD_COPY = {
	"newton_raphson": {
		"title": "Newton-Raphson",
		"summary": "Full Jacobian update every iteration.",
		"image": Path(__file__).resolve().parent.parent / "assets" / "images" / "newton-raphson.jpeg",
		"details": [
			"Recomputes the Jacobian at each nonlinear iteration, so the step direction stays closely aligned with the current residual surface.",
			"Best when robustness and convergence quality matter more than per-iteration setup cost.",
			"Recommended for strongly nonlinear cases and difficult timestep transitions.",
		],
	},
	"quasi_newton": {
		"title": "Quasi-Newton",
		"summary": "Reuses or approximates Jacobian information.",
		"image": Path(__file__).resolve().parent.parent / "assets" / "images" / "quasi-newton.png",
		"details": [
			"Avoids rebuilding the full Jacobian every iteration, reducing assembly cost when the residual surface evolves smoothly.",
			"Best when iteration speed matters and the current case does not require the full Newton correction every step.",
			"Recommended for exploratory runs, lighter nonlinearity, or when Jacobian assembly dominates runtime.",
		],
	},
}


class _MethodImage(QLabel):
	def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._pixmap = QPixmap(str(image_path))
		self.setObjectName("methodImage")
		self.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.setMinimumHeight(320)
		self.setScaledContents(False)

	def resizeEvent(self, event) -> None:  # noqa: N802
		super().resizeEvent(event)
		if self._pixmap.isNull():
			self.setText("Method image not found")
			return
		self.setPixmap(
			self._pixmap.scaled(
				self.width() - 8,
				self.height() - 8,
				Qt.AspectRatioMode.KeepAspectRatio,
				Qt.TransformationMode.SmoothTransformation,
			)
		)


class _MethodCard(QFrame):
	def __init__(self, method_key: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._method_key = method_key
		self.setObjectName("methodInfoCard")
		self._opacity = QGraphicsOpacityEffect(self)
		self.setGraphicsEffect(self._opacity)
		root = QVBoxLayout(self)
		root.setContentsMargins(20, 18, 20, 18)
		root.setSpacing(12)

		copy = _METHOD_COPY[method_key]
		title_row = QHBoxLayout()
		self._title = QLabel(copy["title"])
		self._title.setObjectName("methodCardTitle")
		self._summary = QLabel(copy["summary"])
		self._summary.setObjectName("methodCardSummary")
		title_row.addWidget(self._title)
		title_row.addStretch()
		title_row.addWidget(self._summary)
		root.addLayout(title_row)

		self._detail_labels: list[QLabel] = []
		for line in copy["details"]:
			label = QLabel(line)
			label.setWordWrap(True)
			label.setObjectName("methodBodyText")
			root.addWidget(label)
			self._detail_labels.append(label)

		self._image = _MethodImage(copy["image"])
		root.addWidget(self._image, 1)
		self.set_active(False)

	def set_active(self, active: bool) -> None:
		self.setProperty("activeMethod", active)
		self._opacity.setOpacity(1.0 if active else 0.44)
		self._title.setStyleSheet(f"color: {'#1F2937' if active else '#6F7B8A'}; font-size: 11pt; font-weight: 700;")
		self._summary.setStyleSheet(f"color: {'#0F5C8E' if active else '#8C97A6'}; font-size: 8.8pt; font-weight: 700;")
		for label in self._detail_labels:
			label.setStyleSheet(f"color: {'#5B6676' if active else '#93A1B2'}; font-size: 8.8pt;")
		self.style().unpolish(self)
		self.style().polish(self)


class MethodsPage(QWidget):
	methodSaved = Signal(object)

	def __init__(self) -> None:
		super().__init__()
		self._saved_method = "newton_raphson"
		self._draft_method = "newton_raphson"
		self._confirmed = False

		outer = QVBoxLayout(self)
		outer.setContentsMargins(0, 0, 0, 0)
		outer.setSpacing(0)
		scroll = QScrollArea(self)
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		outer.addWidget(scroll)

		content = QWidget()
		scroll.setWidget(content)
		root = QVBoxLayout(content)
		root.setContentsMargins(18, 16, 18, 18)
		root.setSpacing(12)

		hdr = QHBoxLayout()
		title_block = QVBoxLayout()
		title_block.setSpacing(3)
		title = QLabel("Methods")
		title.setObjectName("pageTitle")
		subtitle = QLabel("Choose the nonlinear iteration strategy used for the current project configuration.")
		subtitle.setObjectName("pageSubtitle")
		title_block.addWidget(title)
		title_block.addWidget(subtitle)
		hdr.addLayout(title_block)
		hdr.addStretch()
		root.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		root.addWidget(sep)

		control_panel = QFrame()
		control_panel.setObjectName("pageSectionPanel")
		control_root = QVBoxLayout(control_panel)
		control_root.setContentsMargins(18, 16, 18, 16)
		control_root.setSpacing(10)

		mode_row = QHBoxLayout()
		mode_row.setSpacing(8)
		self._group = QButtonGroup(self)
		self._group.setExclusive(True)
		self.btn_newton = QPushButton("Newton-Raphson")
		self.btn_newton.setObjectName("methodToggleButton")
		self.btn_newton.setCheckable(True)
		self.btn_quasi = QPushButton("Quasi-Newton")
		self.btn_quasi.setObjectName("methodToggleButton")
		self.btn_quasi.setCheckable(True)
		self._group.addButton(self.btn_newton)
		self._group.addButton(self.btn_quasi)
		mode_row.addWidget(self.btn_newton, 1)
		mode_row.addWidget(self.btn_quasi, 1)
		control_root.addLayout(mode_row)

		save_row = QHBoxLayout()
		save_row.setSpacing(10)
		self._status_chip = QLabel("")
		self._status_chip.setObjectName("pageStatusChip")
		save_row.addWidget(self._status_chip)
		save_row.addStretch(1)
		self.btn_save_method = QPushButton("Simpan Method")
		self.btn_save_method.setObjectName("constraintSaveButton")
		self.btn_save_method.setMinimumSize(142, 42)
		self.btn_save_method.setCursor(Qt.CursorShape.PointingHandCursor)
		save_row.addWidget(self.btn_save_method)
		control_root.addLayout(save_row)
		root.addWidget(control_panel)

		cards_row = QHBoxLayout()
		cards_row.setSpacing(12)
		self.newton_card = _MethodCard("newton_raphson")
		self.quasi_card = _MethodCard("quasi_newton")
		cards_row.addWidget(self.newton_card, 1)
		cards_row.addWidget(self.quasi_card, 1)
		root.addLayout(cards_row)
		root.addStretch(1)

		self.btn_newton.clicked.connect(lambda: self._activate_method("newton_raphson"))
		self.btn_quasi.clicked.connect(lambda: self._activate_method("quasi_newton"))
		self.btn_save_method.clicked.connect(self._save_method)
		self._set_draft_method("newton_raphson")

	def set_project(self, project_config: ProjectConfig) -> None:
		method = project_config.methods.active_method
		if method not in _METHOD_COPY:
			method = "newton_raphson"
		self._saved_method = method
		self._confirmed = project_config.constraints.methods_confirmed
		self._set_draft_method(method)

	def _set_draft_method(self, method_key: str) -> None:
		self._draft_method = method_key
		self.btn_newton.setChecked(method_key == "newton_raphson")
		self.btn_quasi.setChecked(method_key == "quasi_newton")
		self.newton_card.set_active(method_key == "newton_raphson")
		self.quasi_card.set_active(method_key == "quasi_newton")

		if self._confirmed:
			title = _METHOD_COPY[self._saved_method]["title"]
			self._status_chip.setText(f"Aktif untuk Run: {title}")
			self._status_chip.setProperty("chipKind", "ok")
		else:
			self._status_chip.setText("Belum Disimpan")
			self._status_chip.setProperty("chipKind", "empty")
		self._status_chip.style().unpolish(self._status_chip)
		self._status_chip.style().polish(self._status_chip)
		self.btn_save_method.setEnabled((not self._confirmed) or self._draft_method != self._saved_method)

	def _activate_method(self, method_key: str) -> None:
		self._set_draft_method(method_key)

	def _save_method(self) -> None:
		self._saved_method = self._draft_method
		self._confirmed = True
		self._set_draft_method(self._draft_method)
		self.methodSaved.emit(MethodConfig(active_method=self._draft_method))

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QVBoxLayout,
	QWidget,
)

from engine.domain.project import ProjectConfig
from windows.ui_kit import make_card


def _form(parent: QWidget | None = None) -> QFormLayout:
	f = QFormLayout(parent)
	f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
	f.setHorizontalSpacing(14)
	f.setVerticalSpacing(8)
	f.setContentsMargins(10, 10, 10, 10)
	return f


class ModelPage(QWidget):
	projectChanged = Signal(str, str, str)

	def __init__(self) -> None:
		super().__init__()

		outer = QVBoxLayout(self)
		outer.setSpacing(8)
		outer.setContentsMargins(14, 14, 14, 14)

		# ── Page header ───────────────────────────────────────────────
		hdr = QHBoxLayout()
		title = QLabel("Model")
		title.setObjectName("pageTitle")
		hdr.addWidget(title)
		hdr.addStretch()
		outer.addLayout(hdr)

		sep = QFrame()
		sep.setFrameShape(QFrame.Shape.HLine)
		sep.setObjectName("pageDivider")
		outer.addWidget(sep)

		# ── Group: Project Info ───────────────────────────────────────
		card_proj, lay_proj = make_card("P", "#0F5C8E", "Project Info", "Identitas dan deskripsi project")
		frm_proj = _form()
		self.name_input = QLineEdit()
		self.description_input = QLineEdit()
		self.case_name_input = QLineEdit()
		frm_proj.addRow("Nama Project", self.name_input)
		frm_proj.addRow("Deskripsi", self.description_input)
		frm_proj.addRow("Nama Case", self.case_name_input)
		lay_proj.addLayout(frm_proj)
		outer.addWidget(card_proj)

		outer.addStretch()

		# ── Wire signals ──────────────────────────────────────────────
		self.name_input.editingFinished.connect(self._emit_change)
		self.description_input.editingFinished.connect(self._emit_change)
		self.case_name_input.editingFinished.connect(self._emit_change)

	def set_project(self, project_config: ProjectConfig) -> None:
		blockers = [
			QSignalBlocker(self.name_input),
			QSignalBlocker(self.description_input),
			QSignalBlocker(self.case_name_input),
		]
		self.name_input.setText(project_config.name)
		self.description_input.setText(project_config.description)
		self.case_name_input.setText(project_config.run.case_name)
		del blockers

	def _emit_change(self) -> None:
		self.projectChanged.emit(
			self.name_input.text(),
			self.description_input.text(),
			self.case_name_input.text(),
		)

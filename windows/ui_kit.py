from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
	QAbstractSpinBox,
	QDoubleSpinBox,
	QFrame,
	QHBoxLayout,
	QInputDialog,
	QLabel,
	QLineEdit,
	QMenu,
	QMessageBox,
	QSizePolicy,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)


def make_card(
	icon_letter: str,
	icon_color: str,
	title: str,
	subtitle: str,
	*,
	show_icon: bool = True,
) -> tuple[QFrame, QVBoxLayout]:
	"""Build a white card (hairline border, no drop shadow) with a circular
	icon badge + title/subtitle header.

	Shared visual building block used across the Grid, Model, Solver and
	Initial Conditions pages so section headers look consistent app-wide.
	"""
	card = QFrame()
	card.setObjectName("uiKitCard")
	card.setStyleSheet("""
		QFrame#uiKitCard {
			background-color: #ffffff;
			border: 1px solid #D7DEE7;
			border-radius: 8px;
		}
	""")

	lay = QVBoxLayout(card)
	lay.setContentsMargins(18, 16, 18, 16)
	lay.setSpacing(12)

	header = QHBoxLayout()
	header.setSpacing(10)

	if show_icon:
		icon_lbl = QLabel(icon_letter)
		icon_lbl.setFixedSize(32, 32)
		icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
		icon_lbl.setStyleSheet(
			f"background-color: {icon_color}; color: #ffffff; border-radius: 16px;"
			"font-size: 11pt; font-weight: 700;"
		)
		header.addWidget(icon_lbl)

	title_block = QVBoxLayout()
	title_block.setSpacing(0)
	title_lbl = QLabel(title)
	title_lbl.setStyleSheet("font-size: 11pt; font-weight: 700; color: #1F2937;")
	title_block.addWidget(title_lbl)
	sub_lbl = QLabel(subtitle)
	sub_lbl.setStyleSheet("font-size: 8pt; color: #93A1B2;")
	title_block.addWidget(sub_lbl)
	header.addLayout(title_block)
	header.addStretch(1)
	lay.addLayout(header)

	sep = QFrame()
	sep.setFrameShape(QFrame.Shape.HLine)
	sep.setStyleSheet("background-color: #EEF2F6; border: none; max-height: 1px;")
	lay.addWidget(sep)

	return card, lay


def make_hero_banner(stat_tags: list[str]) -> tuple[QFrame, list[QLabel]]:
	"""Build a flat summary strip with N stat blocks, returning their value labels.

	Quiet by design: a tinted surface and a hairline border carry the "this is
	a summary" signal, not a gradient fill — the accent color is reserved for
	the values themselves.
	"""
	card = QFrame()
	card.setObjectName("uiKitHero")
	card.setStyleSheet("""
		QFrame#uiKitHero {
			background-color: #F1F4F8;
			border: 1px solid #D7DEE7;
			border-radius: 8px;
		}
	""")

	lay = QHBoxLayout(card)
	lay.setContentsMargins(22, 14, 22, 14)
	lay.setSpacing(26)

	value_labels: list[QLabel] = []
	for i, tag in enumerate(stat_tags):
		if i > 0:
			divider = QFrame()
			divider.setFrameShape(QFrame.Shape.VLine)
			divider.setStyleSheet("background-color: #D7DEE7; max-width: 1px;")
			lay.addWidget(divider)

		block = QVBoxLayout()
		block.setSpacing(2)
		tag_lbl = QLabel(tag)
		tag_lbl.setStyleSheet(
			"font-size: 7.5pt; font-weight: 700; color: #5B6676;"
			"letter-spacing: 1.2px; background: transparent;"
		)
		block.addWidget(tag_lbl)
		val_lbl = QLabel("-")
		val_lbl.setStyleSheet(
			"font-size: 14pt; font-weight: 700; color: #0F5C8E; background: transparent;"
		)
		block.addWidget(val_lbl)
		value_labels.append(val_lbl)
		lay.addLayout(block)

	lay.addStretch(1)
	return card, value_labels


class SpinBoxInputBlocker(QObject):
	"""Blocks wheel scrolling and Up/Down/PageUp/PageDown stepping on a spin box.

	Fields wired through enable_precise_edit() are meant to be set only via
	the right-click "Set nilai presisi…" dialog, so an accidental scroll or
	arrow-key press over a focused field must not silently change a value.
	"""

	_STEP_KEYS = (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown)

	def eventFilter(self, watched: QObject, event: QEvent) -> bool:
		if event.type() == QEvent.Type.Wheel:
			return True
		if event.type() == QEvent.Type.KeyPress and event.key() in self._STEP_KEYS:
			return True
		return False


def enable_precise_edit(
	parent: QWidget, spin: QAbstractSpinBox, label: str, blockers: list[SpinBoxInputBlocker]
) -> QAbstractSpinBox:
	"""Make a spin box edit-via-dialog-only: typing, wheel scroll, and Up/Down
	stepping are disabled; right-click (or the field's context menu) opens a
	"Set nilai presisi…" dialog that is the only way to change the value.

	Also flattens the field's visual style so it reads as a value sized to
	its own content rather than an editable box stretched across the row —
	`blockers` must be a list owned by the caller (e.g. an instance attribute)
	to keep the installed event filters alive.
	"""
	spin.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
	spin.customContextMenuRequested.connect(
		lambda pos, s=spin, lbl=label: _show_field_menu(parent, s, lbl, s.mapToGlobal(pos))
	)
	spin.setProperty("flatValue", True)
	# Hover/focus colors live solely in style.qss's [flatValue="true"] rules —
	# this widget-level sheet used to also set its own :hover background,
	# which (since a widget-level sheet always wins over the app sheet)
	# silently fought with the QLineEdit child's own [flatValue] hover color
	# below, making the field flash two slightly different tints depending on
	# whether the frame or the inner line edit caught the hover. One color,
	# defined once, keeps the hover reading as a single flat highlight.
	spin.setStyleSheet("""
		QAbstractSpinBox {
			background: transparent;
			border: 1px solid transparent;
			border-radius: 8px;
			padding: 6px 14px;
			font-size: 10pt;
			font-weight: 700;
			color: #1F2937;
		}
		QAbstractSpinBox::up-button,
		QAbstractSpinBox::down-button {
			width: 0px;
			height: 0px;
			border: none;
			background: transparent;
		}
	""")
	spin.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
	spin.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
	spin.setFocusPolicy(Qt.FocusPolicy.NoFocus)
	spin.setCursor(Qt.CursorShape.PointingHandCursor)
	spin.setToolTip(f"Klik kanan untuk ubah nilai {label}")
	# The visible text area is actually spin's internal QLineEdit child, which
	# is what the cursor is over on right-click — wire it directly too instead
	# of relying on the event bubbling up to the spin box's own policy.
	line_edit = spin.lineEdit()
	if line_edit is not None:
		line_edit.setProperty("flatValue", True)
		line_edit.setStyleSheet("""
			QLineEdit {
				background: transparent;
				border: none;
				padding: 0;
				margin: 0;
				font-size: 10pt;
				font-weight: 700;
				color: #1F2937;
			}
		""")
		line_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		line_edit.customContextMenuRequested.connect(
			lambda pos, s=spin, le=line_edit, lbl=label: _show_field_menu(parent, s, lbl, le.mapToGlobal(pos))
		)
		# These fields are edit-via-dialog-only: typing, wheel scroll, and
		# Up/Down stepping are all disabled here; the dialog still changes
		# the value through setValue(), which setReadOnly() does not block.
		line_edit.setReadOnly(True)
		line_edit.setCursor(Qt.CursorShape.PointingHandCursor)
		line_edit.setToolTip(f"Klik kanan untuk ubah nilai {label}")
		blocker = SpinBoxInputBlocker(parent)
		spin.installEventFilter(blocker)
		line_edit.installEventFilter(blocker)
		blockers.append(blocker)
	return spin


def _show_field_menu(parent: QWidget, spin: QAbstractSpinBox, label: str, global_pos) -> None:
	menu = QMenu(parent)
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
	""")
	act_set_value = menu.addAction("  Set nilai presisi…")
	action = menu.exec(global_pos)
	if action == act_set_value:
		_show_precise_value_dialog(parent, spin, label)


def _show_precise_value_dialog(parent: QWidget, spin: QAbstractSpinBox, label: str) -> None:
	current_text = spin.textFromValue(spin.value()) if isinstance(spin, QDoubleSpinBox) else str(spin.value())
	text, ok = QInputDialog.getText(
		parent,
		f"Set Nilai — {label}",
		"Nilai (notasi scientific seperti 1e-5 didukung):",
		QLineEdit.EchoMode.Normal,
		current_text,
	)
	if not ok:
		return
	raw = text.strip().replace(",", ".")
	try:
		value = float(raw)
	except ValueError:
		QMessageBox.warning(parent, "Nilai Tidak Valid", f"'{text}' bukan angka yang valid.")
		return
	if isinstance(spin, QSpinBox):
		value_int = int(round(value))
		if not (spin.minimum() <= value_int <= spin.maximum()):
			QMessageBox.warning(
				parent, "Nilai Luar Rentang",
				f"Nilai harus berupa bilangan bulat antara {spin.minimum()} dan {spin.maximum()}.",
			)
			return
		spin.setValue(value_int)
		return
	if not (spin.minimum() <= value <= spin.maximum()):
		QMessageBox.warning(
			parent, "Nilai Luar Rentang",
			f"Nilai harus berada pada rentang {spin.minimum()} – {spin.maximum()}.",
		)
		return
	spin.setValue(value)

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtWidgets import QApplication

from windows.main_window import MainWindow

def create_application(argv: Sequence[str] | None = None) -> QApplication:
	app = QApplication(list(argv) if argv is not None else sys.argv)
	app.setApplicationName("CoreReservoir")
	app.setOrganizationName("CoreReservoir")
	_load_stylesheet(app)
	return app

def main(argv: Sequence[str] | None = None) -> int:
	app = create_application(argv)
	window = MainWindow()
	window.show()
	return app.exec()


def _load_stylesheet(app: QApplication) -> None:
	stylesheet_path = Path(__file__).resolve().parent.parent / "assets" / "style.qss"
	if not stylesheet_path.exists():
		return

	app.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))

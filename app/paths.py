from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
	"""Root directory the app should resolve bundled data from.

	When running from source, this is the repo root (two levels up from this
	file). When running as a PyInstaller-frozen executable, on-disk source
	layout no longer applies -- bundled data lives under sys._MEIPASS instead.
	"""
	if getattr(sys, "frozen", False):
		return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
	return Path(__file__).resolve().parent.parent


def asset_path(*parts: str) -> Path:
	return app_root().joinpath("assets", *parts)

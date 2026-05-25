from pathlib import Path
import sys

if __package__ in (None, ""):
	workspace_root = Path(__file__).resolve().parent.parent
	if str(workspace_root) not in sys.path:
		sys.path.insert(0, str(workspace_root))

from app.bootstrap import main

if __name__ == "__main__":
	raise SystemExit(main())

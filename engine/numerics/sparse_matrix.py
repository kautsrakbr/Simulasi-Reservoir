from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SparseMatrixCOO:
	rows: list[int] = field(default_factory=list)
	cols: list[int] = field(default_factory=list)
	values: list[float] = field(default_factory=list)

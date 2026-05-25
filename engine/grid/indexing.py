from __future__ import annotations


def flatten_index(i: int, j: int, k: int, nx: int, ny: int) -> int:
	return k * nx * ny + j * nx + i

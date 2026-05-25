from __future__ import annotations


def interpolate_relperm(table: list[tuple[float, float]], saturation: float) -> float:
	if not table:
		raise ValueError("Tabel relperm kosong.")
	if saturation <= table[0][0]:
		return table[0][1]
	if saturation >= table[-1][0]:
		return table[-1][1]

	for left, right in zip(table, table[1:]):
		s_left, value_left = left
		s_right, value_right = right
		if s_left <= saturation <= s_right:
			weight = (saturation - s_left) / (s_right - s_left)
			return value_left + weight * (value_right - value_left)

	return table[-1][1]


def evaluate_cell_relperm(rock_tables: dict[str, list[tuple[float, float]]], sw: float, sg: float) -> dict[str, float]:
	return {
		"krw": interpolate_relperm(rock_tables.get("krw", [(0.0, 0.0), (1.0, 1.0)]), sw),
		"krg": interpolate_relperm(rock_tables.get("krg", [(0.0, 0.0), (1.0, 1.0)]), sg),
	}

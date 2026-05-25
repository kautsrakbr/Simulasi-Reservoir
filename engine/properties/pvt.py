from __future__ import annotations


def interpolate_pvt(table: list[tuple[float, float]], pressure: float) -> float:
	if not table:
		raise ValueError("Tabel PVT kosong.")
	if pressure <= table[0][0]:
		return table[0][1]
	if pressure >= table[-1][0]:
		return table[-1][1]

	for left, right in zip(table, table[1:]):
		p_left, value_left = left
		p_right, value_right = right
		if p_left <= pressure <= p_right:
			weight = (pressure - p_left) / (p_right - p_left)
			return value_left + weight * (value_right - value_left)

	return table[-1][1]


def evaluate_cell_pvt(reference_data: object, table: list[tuple[float, float]], pressure: float) -> float:
	del reference_data
	return interpolate_pvt(table, pressure)

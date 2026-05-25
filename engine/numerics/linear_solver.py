from __future__ import annotations


def _copy_matrix(matrix: list[list[float]]) -> list[list[float]]:
	return [list(row) for row in matrix]


def _copy_vector(vector: list[float]) -> list[float]:
	return list(vector)


def solve_linear_system(
	matrix: list[list[float]],
	rhs: list[float],
	solver_config: object | None = None,
) -> list[float]:
	del solver_config
	if not matrix:
		return []

	size = len(matrix)
	if len(rhs) != size:
		raise ValueError("Ukuran RHS tidak cocok dengan ukuran matrix.")

	for row in matrix:
		if len(row) != size:
			raise ValueError("Matrix harus berbentuk persegi untuk solver saat ini.")

	a = _copy_matrix(matrix)
	b = _copy_vector(rhs)
	epsilon = 1e-14

	for pivot in range(size):
		pivot_row = pivot
		pivot_value = abs(a[pivot][pivot])
		for candidate in range(pivot + 1, size):
			candidate_value = abs(a[candidate][pivot])
			if candidate_value > pivot_value:
				pivot_value = candidate_value
				pivot_row = candidate

		if pivot_value < epsilon:
			raise ValueError("Matrix singular atau hampir singular pada eliminasi Gaussian.")

		if pivot_row != pivot:
			a[pivot], a[pivot_row] = a[pivot_row], a[pivot]
			b[pivot], b[pivot_row] = b[pivot_row], b[pivot]

		pivot_element = a[pivot][pivot]
		for row in range(pivot + 1, size):
			factor = a[row][pivot] / pivot_element
			if abs(factor) < epsilon:
				continue
			for col in range(pivot, size):
				a[row][col] -= factor * a[pivot][col]
			b[row] -= factor * b[pivot]

	x = [0.0 for _ in range(size)]
	for row in range(size - 1, -1, -1):
		sum_ax = 0.0
		for col in range(row + 1, size):
			sum_ax += a[row][col] * x[col]
		pivot_element = a[row][row]
		if abs(pivot_element) < epsilon:
			raise ValueError("Pivot nol terdeteksi pada back-substitution.")
		x[row] = (b[row] - sum_ax) / pivot_element

	return x

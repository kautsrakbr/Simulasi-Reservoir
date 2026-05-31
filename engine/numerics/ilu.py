from __future__ import annotations

from dataclasses import dataclass, field

from engine.numerics.sparse_matrix import SparseMatrixCOO


@dataclass(slots=True)
class ILU0Preconditioner:
	"""ILU(0) faktorisasi tersimpan dalam format CSR gabungan L+U."""
	n: int = 0
	values: list[float] = field(default_factory=list)
	col_indices: list[int] = field(default_factory=list)
	row_ptr: list[int] = field(default_factory=list)
	diag_index: list[int] = field(default_factory=list)


def _coo_to_sorted_csr(
	matrix: SparseMatrixCOO,
) -> tuple[list[float], list[int], list[int], int]:
	"""Konversi COO ke CSR dengan kolom terurut per baris. Entri duplikat dijumlahkan."""
	if not matrix.rows:
		return [], [], [0], 0

	n = max(max(matrix.rows), max(matrix.cols)) + 1

	entry: dict[tuple[int, int], float] = {}
	for r, c, v in zip(matrix.rows, matrix.cols, matrix.values):
		key = (r, c)
		entry[key] = entry.get(key, 0.0) + v

	sorted_entries = sorted(entry.items())

	row_ptr = [0] * (n + 1)
	for (r, _c), _v in sorted_entries:
		row_ptr[r + 1] += 1
	for i in range(n):
		row_ptr[i + 1] += row_ptr[i]

	nnz = len(sorted_entries)
	values: list[float] = [0.0] * nnz
	col_indices: list[int] = [0] * nnz
	for k, ((_, c), v) in enumerate(sorted_entries):
		values[k] = v
		col_indices[k] = c

	return values, col_indices, row_ptr, n


def build_ilu0(matrix: SparseMatrixCOO) -> ILU0Preconditioner:
	"""Bangun preconditioner ILU(0) dari matrix sparse format COO.

	Algoritma Saad (Iterative Methods for Sparse Linear Systems, Algorithm 10.4).
	Faktorisasi in-place hanya pada posisi sparsity asli (zero fill-in).
	"""
	values, col_indices, row_ptr, n = _coo_to_sorted_csr(matrix)

	if n == 0:
		return ILU0Preconditioner(n=0)

	diag_index: list[int] = [-1] * n
	for i in range(n):
		for k in range(row_ptr[i], row_ptr[i + 1]):
			if col_indices[k] == i:
				diag_index[i] = k
				break

	for i in range(1, n):
		for k in range(row_ptr[i], row_ptr[i + 1]):
			j = col_indices[k]
			if j >= i:
				break  # kolom terurut; lewati diagonal dan entri upper
			diag_j = diag_index[j]
			if diag_j < 0 or abs(values[diag_j]) < 1e-14:
				continue
			factor = values[k] / values[diag_j]
			values[k] = factor  # simpan multiplier L di tempat entri bawah diagonal

			# Update entri upper row i menggunakan row j — hanya di posisi yang ada
			kk = k + 1
			jj = diag_j + 1
			while kk < row_ptr[i + 1] and jj < row_ptr[j + 1]:
				col_kk = col_indices[kk]
				col_jj = col_indices[jj]
				if col_kk == col_jj:
					values[kk] -= factor * values[jj]
					kk += 1
					jj += 1
				elif col_kk < col_jj:
					kk += 1
				else:
					jj += 1

	return ILU0Preconditioner(
		n=n,
		values=values,
		col_indices=col_indices,
		row_ptr=row_ptr,
		diag_index=diag_index,
	)


def apply_ilu(preconditioner: ILU0Preconditioner, rhs: list[float]) -> list[float]:
	"""Selesaikan (L*U)*x = rhs via forward/back substitution.

	L: unit lower triangular — entri di bawah diagonal adalah multiplier.
	U: upper triangular — termasuk diagonal yang sudah dimodifikasi.
	"""
	n = preconditioner.n
	if n == 0 or not rhs:
		return list(rhs)

	values = preconditioner.values
	col_indices = preconditioner.col_indices
	row_ptr = preconditioner.row_ptr
	diag_index = preconditioner.diag_index

	b = list(rhs) if len(rhs) >= n else list(rhs) + [0.0] * (n - len(rhs))

	# Forward substitution: solve L*y = b (L unit lower triangular)
	y: list[float] = [0.0] * n
	for i in range(n):
		s = b[i]
		for k in range(row_ptr[i], row_ptr[i + 1]):
			j = col_indices[k]
			if j >= i:
				break
			s -= values[k] * y[j]
		y[i] = s

	# Back substitution: solve U*x = y (U upper triangular)
	x: list[float] = [0.0] * n
	for i in range(n - 1, -1, -1):
		s = y[i]
		diag_k = diag_index[i]
		if diag_k < 0:
			x[i] = s
			continue
		for k in range(diag_k + 1, row_ptr[i + 1]):
			j = col_indices[k]
			s -= values[k] * x[j]
		diag_val = values[diag_k]
		x[i] = s / diag_val if abs(diag_val) > 1e-14 else s

	return x

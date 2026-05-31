from __future__ import annotations

from engine.numerics.ilu import ILU0Preconditioner, apply_ilu
from engine.numerics.sparse_matrix import SparseMatrixCOO


def _dot(a: list[float], b: list[float]) -> float:
	return sum(x * y for x, y in zip(a, b))


def _axpy(alpha: float, x: list[float], y: list[float]) -> list[float]:
	"""Hitung alpha*x + y."""
	return [alpha * xi + yi for xi, yi in zip(x, y)]


def _scale(alpha: float, x: list[float]) -> list[float]:
	return [alpha * xi for xi in x]


def _norm2(v: list[float]) -> float:
	return sum(xi * xi for xi in v) ** 0.5


def _matvec(matrix: SparseMatrixCOO, x: list[float], n: int) -> list[float]:
	"""Perkalian sparse matrix-vektor A*x menggunakan format COO."""
	result = [0.0] * n
	for r, c, v in zip(matrix.rows, matrix.cols, matrix.values):
		if c < len(x):
			result[r] += v * x[c]
	return result


def solve_bicgstab(
	matrix: SparseMatrixCOO,
	rhs: list[float],
	preconditioner: ILU0Preconditioner | None = None,
	max_iter: int = 500,
	tolerance: float = 1e-8,
) -> list[float]:
	"""Selesaikan A*x = b menggunakan BiCGSTAB dengan preconditioner opsional.

	Algoritma Van der Vorst (1992). Jika preconditioner None, berjalan tanpa preconditioning.
	Mengembalikan vektor solusi x.
	"""
	if not rhs:
		return []

	n = len(rhs)

	def matvec(v: list[float]) -> list[float]:
		return _matvec(matrix, v, n)

	def precon(v: list[float]) -> list[float]:
		if preconditioner is None:
			return list(v)
		return apply_ilu(preconditioner, v)

	# x0 = 0, r = b - A*x0 = b
	x = [0.0] * n
	r = list(rhs)

	b_norm = _norm2(rhs)
	if b_norm < 1e-14:
		return [0.0] * n

	# Shadow residual (fixed throughout iteration)
	r_tilde = list(r)

	rho_prev = 1.0
	alpha = 1.0
	omega = 1.0

	v = [0.0] * n
	p = [0.0] * n

	for _iteration in range(max_iter):
		rho = _dot(r_tilde, r)
		if abs(rho) < 1e-14:
			# Breakdown — residual orthogonal to shadow residual
			break

		if _iteration == 0:
			p = list(r)
		else:
			if abs(omega) < 1e-14:
				break
			beta = (rho / rho_prev) * (alpha / omega)
			# p = r + beta * (p - omega * v)
			p_minus_omega_v = _axpy(-omega, v, p)
			p = _axpy(1.0, r, _scale(beta, p_minus_omega_v))

		# p_hat = M^-1 * p
		p_hat = precon(p)
		v = matvec(p_hat)

		r_tilde_v = _dot(r_tilde, v)
		if abs(r_tilde_v) < 1e-14:
			break
		alpha = rho / r_tilde_v

		# s = r - alpha * v
		s = _axpy(-alpha, v, r)

		s_norm = _norm2(s)
		if s_norm / b_norm < tolerance:
			x = _axpy(alpha, p_hat, x)
			break

		# s_hat = M^-1 * s
		s_hat = precon(s)
		t = matvec(s_hat)

		t_dot_t = _dot(t, t)
		if abs(t_dot_t) < 1e-14:
			break
		omega = _dot(t, s) / t_dot_t

		# x = x + alpha * p_hat + omega * s_hat
		x = _axpy(omega, s_hat, _axpy(alpha, p_hat, x))

		# r = s - omega * t
		r = _axpy(-omega, t, s)

		if _norm2(r) / b_norm < tolerance:
			break

		rho_prev = rho

	return x

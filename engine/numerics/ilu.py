from __future__ import annotations


def build_ilu0(matrix: object) -> object:
	del matrix
	raise NotImplementedError("ILU0 belum diimplementasikan.")


def apply_ilu(preconditioner: object, rhs: object) -> object:
	del preconditioner, rhs
	raise NotImplementedError("Apply ILU belum diimplementasikan.")

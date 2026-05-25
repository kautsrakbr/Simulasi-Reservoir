from __future__ import annotations


def newton_step(*args: object, **kwargs: object) -> object:
	del args, kwargs
	raise NotImplementedError("Newton step belum diimplementasikan.")


def build_newton_rhs(residual: list[float]) -> list[float]:
	return [-value for value in residual]


def apply_newton_update(state_k: object, correction: object) -> object:
	del correction
	return state_k

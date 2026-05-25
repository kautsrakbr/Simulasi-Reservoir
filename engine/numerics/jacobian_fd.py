from __future__ import annotations


def assemble_jacobian_fd(*args: object, **kwargs: object) -> object:
	del args, kwargs
	raise NotImplementedError("Jacobian finite-difference belum diimplementasikan.")


def perturb_pressure(*args: object, **kwargs: object) -> object:
	del args, kwargs
	raise NotImplementedError("Perturb pressure belum diimplementasikan.")


def perturb_sw(*args: object, **kwargs: object) -> object:
	del args, kwargs
	raise NotImplementedError("Perturb sw belum diimplementasikan.")


def perturb_sg(*args: object, **kwargs: object) -> object:
	del args, kwargs
	raise NotImplementedError("Perturb sg belum diimplementasikan.")

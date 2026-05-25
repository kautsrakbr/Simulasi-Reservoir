from __future__ import annotations


def assemble_cell_residual(*args: object, **kwargs: object) -> dict[str, float]:
	del args, kwargs
	raise NotImplementedError("Residual per cell belum diimplementasikan.")


def assemble_full_residual(*args: object, **kwargs: object) -> list[float]:
	del args, kwargs
	raise NotImplementedError("Residual global belum diimplementasikan.")

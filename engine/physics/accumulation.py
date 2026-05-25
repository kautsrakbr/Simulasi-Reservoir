from __future__ import annotations


def compute_effective_pore_volume(cell: object, pressure: float, reference_data: object) -> float:
	del cell, pressure, reference_data
	raise NotImplementedError("Effective pore volume belum diimplementasikan.")


def compute_oil_accumulation(*args: object, **kwargs: object) -> float:
	del args, kwargs
	raise NotImplementedError("Oil accumulation belum diimplementasikan.")


def compute_water_accumulation(*args: object, **kwargs: object) -> float:
	del args, kwargs
	raise NotImplementedError("Water accumulation belum diimplementasikan.")


def compute_gas_accumulation(*args: object, **kwargs: object) -> float:
	del args, kwargs
	raise NotImplementedError("Gas accumulation belum diimplementasikan.")

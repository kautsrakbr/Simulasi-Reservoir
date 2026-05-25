from __future__ import annotations

from engine.domain.project import ReferenceData


def read_reference_data(source: dict[str, float]) -> ReferenceData:
	return ReferenceData(
		reference_depth=source.get("reference_depth", 0.0),
		reference_pressure=source.get("reference_pressure", 0.0),
		oil_density_reference=source.get("oil_density_reference", 0.0),
		water_density_reference=source.get("water_density_reference", 0.0),
		gas_density_reference=source.get("gas_density_reference", 0.0),
		rock_compressibility=source.get("rock_compressibility", 0.0),
		bubble_point_pressure=source.get("bubble_point_pressure", 0.0),
		oil_compressibility_reference=source.get("oil_compressibility_reference", 0.0),
		water_compressibility_reference=source.get("water_compressibility_reference", 0.0),
		gas_compressibility_reference=source.get("gas_compressibility_reference", 0.0),
	)

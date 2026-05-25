from __future__ import annotations

from engine.domain.rock import RelativePermeabilityPoint, RockFluidTable


def read_rock_table(name: str, rows: list[dict[str, float]]) -> RockFluidTable:
	return RockFluidTable(
		name=name,
		points=[
			RelativePermeabilityPoint(
				sw=row.get("sw", 0.0),
				sg=row.get("sg", 0.0),
				kro=row.get("kro", 0.0),
				krw=row.get("krw", 0.0),
				krg=row.get("krg", 0.0),
				pcow=row.get("pcow", 0.0),
				pcgw=row.get("pcgw", 0.0),
			)
			for row in rows
		],
	)

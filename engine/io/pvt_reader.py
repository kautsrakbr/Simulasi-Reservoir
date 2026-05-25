from __future__ import annotations

from engine.domain.fluid import PVTPoint, PVTTable


def read_pvt_table(name: str, rows: list[dict[str, float]]) -> PVTTable:
	return PVTTable(
		name=name,
		points=[
			PVTPoint(
				pressure=row.get("pressure", 0.0),
				bo=row.get("bo", 0.0),
				bw=row.get("bw", 0.0),
				bg=row.get("bg", 0.0),
				mu_o=row.get("mu_o", 0.0),
				mu_w=row.get("mu_w", 0.0),
				mu_g=row.get("mu_g", 0.0),
				rso=row.get("rso", 0.0),
				rsw=row.get("rsw", 0.0),
			)
			for row in rows
		],
	)

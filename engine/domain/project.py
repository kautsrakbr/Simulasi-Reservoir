from __future__ import annotations

from dataclasses import dataclass, field

from engine.domain.grid import GridSpec

@dataclass(slots=True)
class ReferenceData:
	reference_depth: float = 0.0
	reference_pressure: float = 0.0
	oil_density_reference: float = 0.0
	water_density_reference: float = 0.0
	gas_density_reference: float = 0.0
	rock_compressibility: float = 0.0
	bubble_point_pressure: float = 0.0
	oil_compressibility_reference: float = 0.0
	water_compressibility_reference: float = 0.0
	gas_compressibility_reference: float = 0.0

@dataclass(slots=True)
class SolverConfig:
	initial_timestep_days: float = 1.0
	min_timestep_days: float = 0.05
	max_time_days: float = 1.0
	timestep_growth_factor: float = 1.1
	timestep_shrink_factor: float = 0.5
	max_step_retries: int = 8
	max_newton_iterations: int = 10
	residual_tolerance: float = 1e-6
	parameter_tolerance: float = 1e-4
	residual_norm_floor: float = 0.1
	newton_pressure_damping: float = 0.7
	newton_saturation_damping: float = 0.7
	max_pressure_correction: float = 10.0
	max_saturation_correction: float = 0.001

@dataclass(slots=True)
class RunConfig:
	case_name: str = "CoreReservoir Base Case"
	output_frequency: int = 1
	save_reports: bool = True


@dataclass(slots=True)
class InitialConditionConfig:
	reference_depth: float = 0.0
	initial_sw: float = 0.2
	initial_sg: float = 0.0

@dataclass(slots=True)
class ProjectConfig:
	name: str = "CoreReservoir"
	description: str = ""
	reference_data: ReferenceData = field(default_factory=ReferenceData)
	solver: SolverConfig = field(default_factory=SolverConfig)
	run: RunConfig = field(default_factory=RunConfig)
	initial_conditions: InitialConditionConfig = field(default_factory=InitialConditionConfig)
	grid_spec: GridSpec = field(default_factory=GridSpec)
	pvt_tables: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
	rock_tables: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
	is_dirty: bool = False

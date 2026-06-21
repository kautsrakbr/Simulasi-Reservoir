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
	max_newton_iterations: int = 20
	residual_tolerance: float = 1e-5
	parameter_tolerance_pressure: float = 1e-3    # psi-scale Newton convergence floor for delta-P
	parameter_tolerance_saturation: float = 1e-4  # fraction-scale Newton convergence floor for delta-S
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
class PerturbationConfig:
	perturbed_cell_id: int = 0   # 0 = no cell selected
	# delta = 0.0 → auto-compute as initial_value / 15
	# delta > 0   → use this custom value
	delta_P: float = 0.0          # psia
	delta_Sw: float = 0.0         # fraction (0–1)
	delta_Sg: float = 0.0         # fraction (0–1)


@dataclass(slots=True)
class MethodConfig:
	active_method: str = "newton_raphson"  # "newton_raphson" | "quasi_newton"


@dataclass(slots=True)
class WellConfig:
	name: str = ""
	well_type: str = "production"        # "production" | "injection"
	cell_id: int = 1                     # 1-indexed 2D cell (ix + iy*nx + 1)
	well_model: str = "simple_flowrate"  # "simple_flowrate" | "peaceman" | "well_model_3"
	flowrate: float = 100.0              # STB/day (positive for both; type determines sign)


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
	wells: list[WellConfig] = field(default_factory=list)
	perturbation: PerturbationConfig = field(default_factory=PerturbationConfig)
	methods: MethodConfig = field(default_factory=MethodConfig)
	is_dirty: bool = False

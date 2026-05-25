class SimulationError(Exception):
	pass


class ValidationError(SimulationError):
	pass


class NotReadyError(SimulationError):
	pass

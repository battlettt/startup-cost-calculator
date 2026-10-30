"""startup_costs: offline startup cost, runway and break-even estimator."""

from .calculations import analyze, compute_break_even, compute_runway
from .model import LABEL, ValidationError, check, load
from .scenarios import apply_scenario, compare

__version__ = "1.0.0"

__all__ = [
    "LABEL", "ValidationError", "analyze", "apply_scenario", "check", "compare",
    "compute_break_even", "compute_runway", "load",
]

"""
src/castes/
Die 9 Kasten von Myrmex — die Arbeiter des Schwarms.

Diese Phase (Phase 1) definiert die Basisklasse und die ersten echten Kasten.
Weitere Kasten folgen in späteren Prompts.
"""
from .base_caste import BaseCaste
from .placeholder import PlaceholderCaste
from .analyst import AnalystCaste
from .planner import PlannerCaste
from .executor import ExecutorCaste
from .registry import CasteRegistry, get_registry
from .ofat import create_baseline_profile, next_ofat_step, get_current_parameter_name
from .hardware_profile import load_hardware_profile, find_active_profile, HardwareProfile

__all__ = [
    "BaseCaste",
    "PlaceholderCaste",
    "AnalystCaste",
    "PlannerCaste",
    "ExecutorCaste",
    "CasteRegistry",
    "get_registry",
    "create_baseline_profile",
    "next_ofat_step",
    "get_current_parameter_name",
    "load_hardware_profile",
    "find_active_profile",
    "HardwareProfile",
]
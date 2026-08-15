"""
src/loops/
Der Loop-Runner — orchestriert die 4 Schleifen basierend auf dem Arbiter-Plan.
"""
from .loop_runner import LoopRunner
from .loop_definitions import (
    get_loop_definition,
    LOOP_DEFINITIONS,
    LOOP_A_SIMULATION,
    LOOP_B_EXPERIMENT,
    LOOP_C_KNOWLEDGE,
    LOOP_D_COORDINATION,
)

__all__ = [
    "LoopRunner",
    "get_loop_definition",
    "LOOP_DEFINITIONS",
    "LOOP_A_SIMULATION",
    "LOOP_B_EXPERIMENT",
    "LOOP_C_KNOWLEDGE",
    "LOOP_D_COORDINATION",
]
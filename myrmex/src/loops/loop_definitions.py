"""
src/loops/loop_definitions.py
Definition der 4 Schleifen von Myrmex.

Jede Schleife ist eine geordnete Liste von ActionTypes, die in
Sequenz ausgeführt werden. Der LoopRunner nutzt diese Definitionen,
um die richtigen Kasten in der richtigen Reihenfolge aufzurufen.
"""
from __future__ import annotations
from src.models.loop import LoopName, ActionType


# Schleife A: Simulations-Kalibrierung
# Simulator → Analyst → (Kalibrierung)
# Läuft so lange, bis der digitale Zwilling die Realität abbildet.
LOOP_A_SIMULATION: list[ActionType] = [
    ActionType.SIMULATE,
    ActionType.ANALYZE,
]

# Schleife B: Experiment-Iteration
# Planner → Executor → Analyst → Hypothesizer
# Der eigentliche Forschungs-Motor.
LOOP_B_EXPERIMENT: list[ActionType] = [
    ActionType.PLAN,
    ActionType.MEASURE,
    ActionType.ANALYZE,
    ActionType.HYPOTHESIZE,
]

# Schleife C: Wissens-Aufbau
# Analyst → Theorist → Guardian → Archivist
# Sichert, dass nichts Falsches ins Langzeitgedächtnis kommt.
LOOP_C_KNOWLEDGE: list[ActionType] = [
    ActionType.ANALYZE,
    ActionType.CONSOLIDATE,
    ActionType.VALIDATE,
    ActionType.ARCHIVE,
]

# Schleife D: Meta-Koordination
# Arbiter beobachtet alle Pheromone → Welche Schleife braucht Ressourcen?
# Wird vom Arbiter direkt gesteuert, nicht vom LoopRunner.
LOOP_D_COORDINATION: list[ActionType] = []


# Mapping von LoopName zu Schleifen-Definition
LOOP_DEFINITIONS: dict[LoopName, list[ActionType]] = {
    LoopName.LOOP_A_SIMULATION: LOOP_A_SIMULATION,
    LoopName.LOOP_B_EXPERIMENT: LOOP_B_EXPERIMENT,
    LoopName.LOOP_C_KNOWLEDGE: LOOP_C_KNOWLEDGE,
    LoopName.LOOP_D_COORDINATION: LOOP_D_COORDINATION,
}


def get_loop_definition(loop_name: LoopName) -> list[ActionType]:
    """
    Gibt die Aktions-Sequenz für eine Schleife zurück.
    
    Args:
        loop_name: Der Name der Schleife.
    
    Returns:
        Eine Liste von ActionTypes in Ausführungsreihenfolge.
    """
    return LOOP_DEFINITIONS.get(loop_name, [])

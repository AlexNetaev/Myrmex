"""
src/models/loop.py
Definition der 4 Schleifen und ihres Energie-Systems.
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class LoopName(str, Enum):
    """Die 4 Schleifen von Myrmex."""
    LOOP_A_SIMULATION = "loop_a_simulation"       # Simulations-Kalibrierung
    LOOP_B_EXPERIMENT = "loop_b_experiment"       # Experiment-Iteration
    LOOP_C_KNOWLEDGE = "loop_c_knowledge"         # Wissens-Aufbau
    LOOP_D_COORDINATION = "loop_d_coordination"   # Meta-Koordination


class LoopStatus(str, Enum):
    """Der Status einer Schleife."""
    ACTIVE = "active"     # Läuft gerade
    PAUSED = "paused"     # Pausiert (wartet auf Ressourcen)
    BLOCKED = "blocked"   # Blockiert (z.B. durch Warn-Pheromon)
    COMPLETED = "completed"  # Abgeschlossen


class LoopState(BaseModel):
    """
    Der Zustand einer Schleife. Wird in 05_Loops/<loop_name>.json gespeichert.
    """
    model_config = ConfigDict(extra="forbid")
    
    loop_name: LoopName = Field(..., description="Der Name der Schleife")
    status: LoopStatus = Field(default=LoopStatus.PAUSED, description="Aktueller Status")
    
    # Das Energie-System
    energy: float = Field(
        default=100.0, ge=0.0, le=100.0,
        description="Energie-Budget der Schleife (0-100)"
    )
    
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Zeitstempel der letzten Aktivität (UTC)"
    )
    
    iteration_count: int = Field(
        default=0, ge=0,
        description="Wie viele Iterationen diese Schleife bereits durchlaufen hat"
    )

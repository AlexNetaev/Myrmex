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


class ActionType(str, Enum):
    """Die möglichen Aktionstypen einer Schleife."""
    MEASURE = "measure"           # Messung durchführen (+20 Energie)
    SIMULATE = "simulate"         # Simulation ausführen (-5 Energie)
    ANALYZE = "analyze"           # Daten analysieren (-10 Energie)
    CONSOLIDATE = "consolidate"   # Wissen konsolidieren (-5 Energie)
    VALIDATE = "validate"         # Wissen validieren (Guardian)


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


class LoopExecutionResult(BaseModel):
    """Ergebnis einer einzelnen Schleifen-Ausführung."""
    model_config = ConfigDict(extra="forbid")
    
    loop_name: LoopName = Field(..., description="Die ausgeführte Schleife")
    action_type: str = Field(..., description="Der ausgeführte Aktionstyp")
    energy_change: float = Field(..., description="Änderung der Energie (+ oder -)")
    new_energy: float = Field(..., ge=0.0, le=100.0, description="Neue Energie der Schleife")
    iteration_count: int = Field(..., ge=0, description="Neuer Iterationszähler der Schleife")


class LoopCycleResult(BaseModel):
    """Ergebnis eines vollständigen Loop-Zyklus."""
    model_config = ConfigDict(extra="forbid")
    
    loop_executed: LoopName = Field(..., description="Die ausgeführte Schleife")
    action_type: str = Field(..., description="Der ausgeführte Aktionstyp")
    energy_before: float = Field(..., ge=0.0, le=100.0, description="Energie vor der Ausführung")
    energy_after: float = Field(..., ge=0.0, le=100.0, description="Energie nach der Ausführung")
    energy_change: float = Field(..., description="Änderung der Energie (+ oder -)")
    iterations_total: int = Field(..., ge=0, description="Gesamtzahl der Iterationen aller Schleifen")
    evaporation_stats: dict = Field(default_factory=dict, description="Statistiken von evaporate()")

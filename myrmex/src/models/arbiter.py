"""
src/models/arbiter.py
Der Plan des Arbiters (des "Kompass" des Schwarms).
Wird in 00_System/arbiter_plan.json gespeichert.
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from .loop import LoopName


class ArbiterActionType(str, Enum):
    """Die möglichen Aktionen des Arbiters."""
    EXPLORE = "explore"           # Landschaft erkunden (wenig Pheromone)
    FOLLOW_TRAIL = "follow_trail" # Einer starken Spur folgen
    DETOUR = "detour"             # Einer Warnung ausweichen
    CONSOLIDATE = "consolidate"   # Mehr Messungen zum Verifizieren


class ArbiterPlan(BaseModel):
    """
    Der aktuelle Plan des Arbiters. Der Arbiter ist stateless —
    sein "State" ist diese Datei (arbiter_plan.json).
    """
    model_config = ConfigDict(extra="forbid")
    
    # Referenz auf die Ziel-Hierarchie
    directive_summary: str = Field(..., description="Zusammenfassung der Direktive")
    target_crystal_id: str = Field(..., description="ID des Ziel-Kristalls")
    
    # Die aktuelle Priorisierung der Schleifen
    loop_priorities: list[LoopName] = Field(
        default_factory=list,
        description="Priorisierte Reihenfolge der Schleifen"
    )
    
    # Die nächste Aktion
    next_action: ArbiterActionType = Field(
        default=ArbiterActionType.EXPLORE,
        description="Die nächste Aktion des Arbiters"
    )
    next_action_reasoning: str = Field(
        default="",
        description="Begründung für die nächste Aktion"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Zeitstempel der Plan-Erstellung (UTC)"
    )
    
    revision_count: int = Field(
        default=0, ge=0,
        description="Wie oft dieser Plan bereits revidiert wurde"
    )


class ArbiterCycleResult(BaseModel):
    """Ergebnis eines vollständigen Arbiter-Zyklus."""
    model_config = ConfigDict(extra="forbid")
    
    action: ArbiterActionType = Field(..., description="Die gewählte Aktion")
    reasoning: str = Field(..., description="Die Begründung für die Aktion")
    loop_name: LoopName = Field(..., description="Die ausgeführte Schleife")
    loop_results: list = Field(default_factory=list, description="Die Ergebnisse der Schleifen-Ausführung")
    landscape_summary: dict = Field(default_factory=dict, description="Zusammenfassung der Landschaft")

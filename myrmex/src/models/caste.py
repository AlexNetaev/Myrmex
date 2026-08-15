"""
src/models/caste.py
Definition der 9 Kasten (Agenten-Typen).
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from .pheromone import PheromoneType


class CasteName(str, Enum):
    """Die 9 Kasten von Myrmex."""
    HYPOTHESIZER = "hypothesizer"
    SIMULATOR = "simulator"
    PLANNER = "planner"
    EXECUTOR = "executor"
    ANALYST = "analyst"
    THEORIST = "theorist"
    GUARDIAN = "guardian"
    ARCHIVIST = "archivist"
    ARBITER = "arbiter"


class CasteDefinition(BaseModel):
    """
    Definition einer Kaste. Wird in späteren Phesen verwendet,
    um die tatsächlichen Agenten zu konfigurieren.
    """
    model_config = ConfigDict(extra="forbid")
    
    name: CasteName = Field(..., description="Der Name der Kaste")
    role: str = Field(..., description="Die Rolle der Kaste im Schwarm")
    specialization: str = Field(..., description="Die Spezialisierung der Kaste")
    
    # Die Pheromon-Typen, die diese Kaste lesen und schreiben darf
    reads_pheromones: list[PheromoneType] = Field(
        default_factory=list,
        description="Welche Pheromon-Typen diese Kaste lesen darf"
    )
    writes_pheromones: list[PheromoneType] = Field(
        default_factory=list,
        description="Welche Pheromon-Typen diese Kaste schreiben darf"
    )


class CasteRegistry(BaseModel):
    """
    Die Registry aller 9 Kasten. Stellt sicher, dass alle Kasten
    definiert sind und keine Duplikate existieren.
    """
    model_config = ConfigDict(extra="forbid")
    
    castes: dict[CasteName, CasteDefinition] = Field(
        default_factory=dict,
        description="Alle definierten Kasten"
    )
    
    def get_default_registry(self) -> "CasteRegistry":
        """Erstellt die Standard-Registry mit allen 9 Kasten."""
        # Hinweis: Diese Methode wird in Phase 1 nur als Platzhalter angelegt.
        # Die tatsächliche Implementierung folgt in einem späteren Schritt.
        raise NotImplementedError("CasteRegistry.get_default_registry() wird in Phase 1+ implementiert")

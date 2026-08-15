"""
src/models/pheromone.py
Die Basiseinheit der Myrmex-Kommunikation: das Pheromon.
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class PheromoneType(str, Enum):
    """Die drei Pheromon-Typen."""
    TRAIL = "trail"       # 🟢 Flüchtige Information
    CRYSTAL = "crystal"   # 💎 Gesicherte Erkenntnis
    WARNING = "warning"   # 🔴 Negatives Signal


class Pheromone(BaseModel):
    """
    Ein einzelnes Pheromon im Pheromon-Feld.
    
    Pheromone sind die indirekte Kommunikation zwischen den Kasten.
    Sie liegen im Workspace (01_Pheromon_Field/) und werden von anderen
    Kasten "gerochen" (gelesen).
    """
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(..., min_length=1, description="Eindeutige ID des Pheromons")
    type: PheromoneType = Field(..., description="Der Typ des Pheromons")
    
    # Stärke und Verdunstung
    strength: float = Field(
        ..., ge=0.0, le=1.0,
        description="Aktuelle Stärke (0.0-1.0). Kristalle haben immer 1.0."
    )
    age_cycles: int = Field(
        ..., ge=0,
        description="Wie viele Zyklen alt dieses Pheromon ist"
    )
    relevance: float = Field(
        ..., ge=0.0, le=1.0,
        description="Relevanz für das aktuelle Ziel (0.0-1.0)"
    )
    
    # Inhalt und Metadaten
    content: str = Field(..., description="Der eigentliche Inhalt des Pheromons")
    tags: list[str] = Field(default_factory=list, description="Tags zur Kategorisierung")
    source_agent: str = Field(..., min_length=1, description="Welche Kaste das Pheromon gelegt hat")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Zeitstempel der Erstellung (UTC)"
    )
    
    def effective_strength(self) -> float:
        """
        Berechnet die effektive Stärke: strength × relevance × Verdunstung.
        
        Kristalle verdunsten nie (Verdunstung = 1.0).
        Spuren verdunsten mit dem Alter.
        Warnungen verdunsten langsamer als Spuren.
        """
        if self.type == PheromoneType.CRYSTAL:
            evaporation = 1.0
        elif self.type == PheromoneType.WARNING:
            evaporation = max(0.2, 1.0 - (self.age_cycles * 0.03))
        else:  # TRAIL
            evaporation = max(0.1, 1.0 - (self.age_cycles * 0.05))
        
        return self.strength * self.relevance * evaporation

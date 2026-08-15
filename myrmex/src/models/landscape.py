"""
src/models/landscape.py
Zusammenfassung der Pheromon-Landschaft für den Arbiter.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class LandscapeSummary(BaseModel):
    """
    Kompakte Zusammenfassung der Pheromon-Landschaft.
    Wird vom LandscapeAnalyzer erzeugt und vom Arbiter gelesen.
    """
    model_config = ConfigDict(extra="forbid")
    
    # Anzahlen pro Typ
    trail_count: int = Field(default=0, ge=0)
    crystal_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    total_count: int = Field(default=0, ge=0)
    
    # Stärken
    total_effective_strength: float = Field(default=0.0, ge=0.0)
    average_effective_strength: float = Field(default=0.0, ge=0.0)
    max_effective_strength: float = Field(default=0.0, ge=0.0)
    
    # Dichte-Metriken
    is_sparse: bool = Field(
        default=False,
        description="True, wenn die Landschaft 'dünn' ist (wenige Pheromone, wenig Kristalle)"
    )
    has_strong_trail: bool = Field(
        default=False,
        description="True, wenn es einen starken Trail gibt, der zum Ziel führen könnte"
    )
    has_warning_nearby: bool = Field(
        default=False,
        description="True, wenn es Warnungen gibt, die den Weg blockieren könnten"
    )
    
    # Stärkster Trail (für FOLLOW_TRAIL)
    strongest_trail_id: str | None = Field(
        default=None,
        description="ID des stärksten Trails, oder None wenn kein Trail existiert"
    )
    
    # Stärkste Warnung (für DETOUR)
    strongest_warning_id: str | None = Field(
        default=None,
        description="ID der stärksten Warnung, oder None wenn keine Warnung existiert"
    )

"""
src/models/directive.py
Die Ziel-Hierarchie: DIRECTIVE (Nordstern) und ZIEL-KRISTALL (Leuchtturm).
"""
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class Directive(BaseModel):
    """
    Das übergeordnete Ziel der Forschung (Stufe 1 der Ziel-Hierarchie).
    Wird in 00_System/directive.md gespeichert (als Markdown),
    aber hier als strukturiertes Modell definiert.
    """
    model_config = ConfigDict(extra="forbid")
    
    title: str = Field(..., min_length=1, description="Kurzer Titel der Direktive")
    description: str = Field(..., description="Detaillierte Beschreibung des Ziels")
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Kriterien, die erfüllt sein müssen, damit das Ziel erreicht ist"
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Randbedingungen und Einschränkungen"
    )


class TargetCrystal(BaseModel):
    """
    Der Ziel-Kristall (Stufe 2 der Ziel-Hierarchie).
    Definiert konkret, wie "Erfolg" aussieht.
    Wird in 00_System/target_crystal.json gespeichert.
    """
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(..., min_length=1, description="Eindeutige ID des Ziel-Kristalls")
    description: str = Field(..., description="Beschreibung des Ziel-Zustands")
    
    # Die konkreten Erfolgskriterien als Schlüssel-Wert-Paare
    # z.B. {"ph_end_min": 5.0, "ph_end_max": 6.0, "time_s_max": 30.0}
    criteria: dict[str, float] = Field(
        default_factory=dict,
        description="Konkrete numerische Erfolgskriterien"
    )
    
    achieved: bool = Field(
        default=False,
        description="Ob der Ziel-Kristall bereits erreicht wurde"
    )

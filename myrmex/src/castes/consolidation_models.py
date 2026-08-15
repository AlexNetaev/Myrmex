"""
src/castes/consolidation_models.py
Pydantic-Modelle für die LLM-basierte Wissens-Konsolidierung.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class ContradictionResolution(BaseModel):
    """Eine aufgelöste Widersprüchlichkeit."""
    old_knowledge: str = Field(
        ...,
        description="Die alte Erkenntnis aus der theory_baseline.md",
    )
    new_knowledge: str = Field(
        ...,
        description="Die neue Erkenntnis aus den Analyse-Pheromonen",
    )
    resolution: str = Field(
        ...,
        description="Wie der Widerspruch aufgelöst wurde (welche Version ist korrekt und warum)",
    )


class ConsolidationModel(BaseModel):
    """
    Strukturierte Ausgabe der LLM-basierten Wissens-Konsolidierung.
    Das LLM muss dieses Schema exakt einhalten.
    """
    summary: str = Field(
        ...,
        description=(
            "Kurze Zusammenfassung der Konsolidierung (max. 300 Zeichen). "
            "Fasst zusammen, was neues Wissen hinzugefügt wurde."
        ),
    )
    new_knowledge: str = Field(
        ...,
        description=(
            "Die neuen, konsolidierten Erkenntnisse im Markdown-Format. "
            "Dies wird an die theory_baseline.md angehängt. "
            "Verwende klare, wissenschaftliche Sprache."
        ),
    )
    contradictions_resolved: list[ContradictionResolution] = Field(
        default_factory=list,
        description=(
            "Liste der aufgelösten Widersprüche zwischen neuem und bestehendem Wissen. "
            "Kann leer sein, wenn keine Widersprüche gefunden wurden."
        ),
    )
    deprecated_knowledge: list[str] = Field(
        default_factory=list,
        description=(
            "Liste von Erkenntnissen aus der theory_baseline.md, die durch die neuen "
            "Erkenntnisse veraltet sind und entfernt oder markiert werden sollten. "
            "Kann leer sein, wenn nichts veraltet ist."
        ),
    )
    confidence: str = Field(
        ...,
        description=(
            "Das Vertrauen in die Konsolidierung: 'high', 'medium', oder 'low'. "
            "Basiert auf der Klarheit der neuen Erkenntnisse und der Anzahl der Widersprüche."
        ),
    )

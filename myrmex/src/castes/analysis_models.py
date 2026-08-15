"""
src/castes/analysis_models.py
Pydantic-Modelle für die LLM-basierte Datenanalyse.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class AnalysisFinding(BaseModel):
    """Eine einzelne Erkenntnis aus der Analyse."""
    description: str = Field(
        ...,
        description="Beschreibung der Erkenntnis (z.B. 'Fluoreszenz fällt schneller als simuliert')",
    )
    category: str = Field(
        ...,
        description="Kategorie: 'discrepancy', 'anomaly', 'plateau', 'trend', 'confirmation'",
    )
    significance: str = Field(
        ...,
        description="Bedeutung: 'high', 'medium', 'low'",
    )


class AnalysisModel(BaseModel):
    """
    Strukturierte Ausgabe der LLM-basierten Datenanalyse.
    Das LLM muss dieses Schema exakt einhalten.
    """
    summary: str = Field(
        ...,
        description=(
            "Kurze Zusammenfassung der Analyse (max. 300 Zeichen). "
            "Fasst das wichtigste Ergebnis zusammen."
        ),
    )
    key_findings: list[AnalysisFinding] = Field(
        ...,
        description=(
            "Liste der wichtigsten Erkenntnisse aus dem Vergleich "
            "von Simulation und Realität. Mindestens 1, maximal 5."
        ),
    )
    scientific_interpretation: str = Field(
        ...,
        description=(
            "Wissenschaftliche Interpretation der Ergebnisse. "
            "Erkläre, WARUM die beobachteten Muster auftreten, "
            "basierend auf chemischen/physikalischen Prinzipien. "
            "Beziehe die Fenton-Reaktion und Fluorescein-Kinetik mit ein."
        ),
    )
    recommended_next_steps: str = Field(
        ...,
        description=(
            "Empfehlung für das nächste Experiment. "
            "Sei spezifisch: Welcher Parameter sollte wie geändert werden?"
        ),
    )
    confidence: str = Field(
        ...,
        description=(
            "Das Vertrauen in die Analyse: 'high', 'medium', oder 'low'. "
            "Basiert auf der Datenqualität und der Klarheit der Muster."
        ),
    )

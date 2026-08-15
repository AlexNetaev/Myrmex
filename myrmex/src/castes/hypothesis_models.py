"""
src/castes/hypothesis_models.py
Pydantic-Modelle für die LLM-basierte Hypothesen-Generierung.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class HypothesisModel(BaseModel):
    """
    Strukturierte Ausgabe der LLM-basierten Hypothesen-Generierung.
    Das LLM muss dieses Schema exakt einhalten.
    """
    root_cause_analysis: str = Field(
        ...,
        description=(
            "Die kausale Analyse der beobachteten Diskrepanz. "
            "Erkläre, WARUM das beobachtete Verhalten auftritt, "
            "basierend auf den Analyse-Pheromonen und der Theorie-Baseline."
        ),
    )
    proposed_adjustment: str = Field(
        ...,
        description=(
            "Der konkrete Vorschlag für das nächste Experiment. "
            "Beschreibe, WELCHER Parameter geändert werden sollte und WARUM. "
            "Sei spezifisch (z.B. 'Fluorescein-Konzentration auf 5 µM reduzieren')."
        ),
    )
    testable_prediction: str = Field(
        ...,
        description=(
            "Eine testbare Vorhersage: WENN die Hypothese stimmt, "
            "DANN sollte das nächste Experiment dieses Ergebnis zeigen. "
            "Sei spezifisch und messbar."
        ),
    )
    confidence: str = Field(
        ...,
        description=(
            "Das Vertrauen in die Hypothese: 'high', 'medium', oder 'low'. "
            "Basiert auf der Anzahl und Qualität der unterstützenden Beweise."
        ),
    )
    summary: str = Field(
        ...,
        description=(
            "Eine kurze Zusammenfassung der Hypothese für das Pheromon "
            "(max. 200 Zeichen)."
        ),
    )

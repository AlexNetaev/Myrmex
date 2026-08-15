"""
src/castes/plan_models.py
Pydantic-Modelle für die LLM-basierte Experiment-Planung.
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class ExperimentStrategy(str, Enum):
    """Die möglichen Experiment-Strategien."""
    OFAT = "ofat"                   # One-Factor-at-a-Time (einfach, systematisch)
    DOE = "doe"                     # Design of Experiments (mehrere Faktoren)
    EXPLORATION = "exploration"     # Neuer Bereich des Parameterraums
    REPLICATION = "replication"     # Wiederholung zur Verifikation
    EXPLOITATION = "exploitation"   # Feinoptimierung um ein Optimum


class PlanModel(BaseModel):
    """
    Strukturierte Ausgabe der LLM-basierten Experiment-Planung.
    Das LLM muss dieses Schema exakt einhalten.
    """
    strategy: ExperimentStrategy = Field(
        ...,
        description=(
            "Die gewählte Experiment-Strategie: "
            "'ofat', 'doe', 'exploration', 'replication' oder 'exploitation'."
        ),
    )
    parameter_to_change: str = Field(
        ...,
        description=(
            "Der Name des Parameters, der als nächstes geändert werden soll. "
            "Muss einer der folgenden sein: "
            "'ascorbic_acid_concentration_mm', 'fecl3_concentration_mm', "
            "'h2o2_concentration_mm', 'fluorescein_concentration_mm', "
            "'phosphate_buffer_concentration_mm', 'target_temperature_c', "
            "'mixing_speed_rpm', 'mixing_time_s', 'heating_time_s', "
            "'measurement_interval_ms', 'fluorescence_duration_s'."
        ),
    )
    new_value: float = Field(
        ...,
        description=(
            "Der neue Wert für den Parameter. "
            "Muss physikalisch plausibel sein (z.B. positive Konzentrationen, "
            "Temperaturen im Bereich 20-80°C, etc.)."
        ),
    )
    reasoning: str = Field(
        ...,
        description=(
            "Die wissenschaftliche Begründung für diese Parameter-Wahl. "
            "Erkläre, WARUM genau dieser Parameter geändert werden sollte "
            "und warum genau dieser neue Wert gewählt wurde. "
            "Beziehe die Hypothese und die bisherigen Ergebnisse mit ein."
        ),
    )
    expected_outcome: str = Field(
        ...,
        description=(
            "Was wir vom nächsten Experiment erwarten. "
            "Sei spezifisch und messbar "
            "(z.B. 'Fluoreszenz-Delta sollte sich um 20% reduzieren')."
        ),
    )
    confidence: str = Field(
        ...,
        description=(
            "Das Vertrauen in den Plan: 'high', 'medium', oder 'low'. "
            "Basiert auf der Qualität der Hypothese und der bisherigen Daten."
        ),
    )
    summary: str = Field(
        ...,
        description=(
            "Eine kurze Zusammenfassung des Plans für das Pheromon "
            "(max. 200 Zeichen). Format: 'Ändere <parameter> auf <value> "
            "um <expected_outcome>'."
        ),
    )

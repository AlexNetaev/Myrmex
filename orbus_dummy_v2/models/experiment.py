"""
Pydantic-Modelle für den Hardware-Dummy.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ExperimentJob(BaseModel):
    """Ein Experiment-Job aus der Hardware-Queue."""
    job_id: str = Field(..., description="Eindeutige Job-ID")
    cycle_id: str = Field(..., description="Zyklus-ID (z.B. Cycle_001)")
    simulation_seed: Optional[int] = Field(None, description="Seed für reproduzierbare Simulationen")
    
    # Parameter für Station 1: Preparation
    preparation_params: dict = Field(
        default_factory=dict,
        description="Parameter für Preparation (Reagenzien, Mischzeit, etc.)"
    )
    
    # Parameter für Station 2: Measurement
    measurement_params: dict = Field(
        default_factory=dict,
        description="Parameter für Measurement (Temperatur, Dauer, etc.)"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MeasurementResult(BaseModel):
    """Ergebnis einer Messung."""
    time_ms: int = Field(..., ge=0, description="Zeitstempel in Millisekunden")
    temp_c: float = Field(..., description="Temperatur in °C")
    fluorescence_au: float = Field(..., description="Fluoreszenz in arbitrary units")

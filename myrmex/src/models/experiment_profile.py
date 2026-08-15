"""
src/models/experiment_profile.py
Das Experiment-Profil definiert, WAS erforscht wird.
Es ist experiment-UNABHÄNGIG von den Agenten (Schicht 3 der Architektur).
Wird in 00_System/experiment_profile.yaml gespeichert.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class ReagentDose(BaseModel):
    """Ein einzelnes Reagenz."""
    model_config = ConfigDict(extra="forbid")
    
    reagent_name: str = Field(..., min_length=1, description="Name des Reagenz")
    volume_ul: float = Field(..., ge=0, description="Volumen in Mikroliter (µL)")
    concentration_mm: float = Field(..., ge=0, description="Konzentration in Millimolar (mM)")


class ExperimentProfile(BaseModel):
    """
    Das Experiment-Profil. Definiert, welches Experiment erforscht wird.
    Die Agenten lesen dieses Profil, um zu wissen, WAS sie erforschen.
    """
    model_config = ConfigDict(extra="forbid")
    
    experiment_type: str = Field(
        ..., min_length=1,
        description="Der Typ des Experiments (z.B. 'fenton_fluorescence')"
    )
    
    reagents: list[ReagentDose] = Field(
        default_factory=list,
        description="Die Reagenzien des Experiments"
    )
    
    parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Die Prozess-Parameter (z.B. 'target_temperature_c', 'mixing_speed_rpm')"
    )
    
    # Die Observablen (Messgrößen)
    observables: list[str] = Field(
        default_factory=list,
        description="Die Messgrößen (z.B. 'temp_c', 'fluorescence_raw_au')"
    )
    
    # Die Physik-Modelle, die für dieses Experiment verwendet werden
    physics_models: list[str] = Field(
        default_factory=list,
        description="Die Physik-Modelle (z.B. 'fenton_kinetics', 'henderson_hasselbalch')"
    )

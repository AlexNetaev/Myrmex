"""
src/castes/ofat.py
Deterministische OFAT-Strategie (One Factor At a Time) für den Planner.

Diese Datei enthält keine Kasten-Logik, nur die reine OFAT-Strategie.
Das macht sie einfach testbar und wiederverwendbar.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ParameterConfig:
    """Konfiguration für einen einzelnen OFAT-Parameter."""
    name: str
    min_value: float
    max_value: float
    step: float
    default_value: float


# Die OFAT-Sequenz für das Fenton-Experiment.
# Reihenfolge ist bewusst so gewählt: die chemisch einflussreichsten
# Parameter zuerst (Ascorbinsäure, FeCl3), dann die weniger einflussreichen.
OFAT_PARAMETER_SEQUENCE: list[ParameterConfig] = [
    ParameterConfig(
        name="ascorbic_acid_concentration_mm",
        min_value=1.0,
        max_value=50.0,
        step=5.0,
        default_value=25.0,
    ),
    ParameterConfig(
        name="fecl3_concentration_mm",
        min_value=0.1,
        max_value=5.0,
        step=0.5,
        default_value=1.0,
    ),
    ParameterConfig(
        name="h2o2_concentration_mm",
        min_value=1.0,
        max_value=100.0,
        step=10.0,
        default_value=50.0,
    ),
    ParameterConfig(
        name="fluorescein_concentration_mm",
        min_value=0.001,
        max_value=0.02,
        step=0.005,
        default_value=0.01,
    ),
    ParameterConfig(
        name="phosphate_buffer_concentration_mm",
        min_value=10.0,
        max_value=100.0,
        step=10.0,
        default_value=50.0,
    ),
    ParameterConfig(
        name="target_temperature_c",
        min_value=20.0,
        max_value=75.0,
        step=5.0,
        default_value=37.0,
    ),
]


def create_baseline_profile() -> dict:
    """
    Erstellt ein Basis-Profil mit den Default-Werten aller Parameter.
    Wird verwendet, wenn noch kein Profil existiert.
    
    Returns:
        Ein dict mit 'parameters' und 'ofat_state'.
    """
    parameters = {config.name: config.default_value for config in OFAT_PARAMETER_SEQUENCE}
    ofat_state = {
        "current_parameter_index": 0,
        "parameter_sequence": [config.name for config in OFAT_PARAMETER_SEQUENCE],
        "iterations_completed": 0,
    }
    return {
        "experiment_type": "fenton_fluorescence",
        "parameters": parameters,
        "ofat_state": ofat_state,
    }


def next_ofat_step(profile: dict) -> dict:
    """
    Führt den nächsten OFAT-Schritt aus: variiert den aktuellen Parameter
    um eine Schrittweite. Wenn der Parameter sein Maximum erreicht hat,
    wird er auf das Minimum zurückgesetzt und zum nächsten Parameter
    in der Sequenz gewechselt.
    
    Args:
        profile: Das aktuelle Profil mit 'parameters' und 'ofat_state'.
    
    Returns:
        Ein neues Profil (das alte wird nicht mutiert) mit dem nächsten
        OFAT-Schritt angewendet.
    """
    # Kopiere das Profil, um Mutation zu vermeiden
    new_profile = {
        "experiment_type": profile["experiment_type"],
        "parameters": dict(profile["parameters"]),
        "ofat_state": dict(profile["ofat_state"]),
    }
    
    ofat_state = new_profile["ofat_state"]
    current_index = ofat_state["current_parameter_index"]
    parameter_name = ofat_state["parameter_sequence"][current_index]
    
    # Finde die Konfiguration für diesen Parameter
    param_config = _find_parameter_config(parameter_name)
    if param_config is None:
        # Unbekannter Parameter — überspringe ihn
        ofat_state["current_parameter_index"] = (current_index + 1) % len(ofat_state["parameter_sequence"])
        return new_profile
    
    current_value = new_profile["parameters"].get(parameter_name, param_config.default_value)
    new_value = current_value + param_config.step
    
    if new_value > param_config.max_value:
        # Parameter hat sein Maximum erreicht → zurück zum Minimum,
        # nächster Parameter in der Sequenz
        new_value = param_config.min_value
        ofat_state["current_parameter_index"] = (current_index + 1) % len(ofat_state["parameter_sequence"])
        ofat_state["iterations_completed"] = ofat_state.get("iterations_completed", 0) + 1
    
    # Clamp auf [min, max] (defensiv, gegen Float-Rundungsfehler)
    new_value = max(param_config.min_value, min(param_config.max_value, new_value))
    
    new_profile["parameters"][parameter_name] = new_value
    return new_profile


def _find_parameter_config(parameter_name: str) -> ParameterConfig | None:
    """Findet die ParameterConfig für einen gegebenen Namen."""
    for config in OFAT_PARAMETER_SEQUENCE:
        if config.name == parameter_name:
            return config
    return None


def get_current_parameter_name(profile: dict) -> str | None:
    """Gibt den Namen des aktuell variierten Parameters zurück."""
    ofat_state = profile.get("ofat_state", {})
    current_index = ofat_state.get("current_parameter_index", 0)
    sequence = ofat_state.get("parameter_sequence", [])
    if 0 <= current_index < len(sequence):
        return sequence[current_index]
    return None

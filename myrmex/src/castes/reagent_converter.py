"""
src/castes/reagent_converter.py
Umrechnung von Konzentrationen → Volumina für die Hardware.

Der Planner schreibt die Parameter als Konzentrationen (z.B. fecl3_concentration_mm: 1.0),
aber der Executor erwartet Reagenzien (mit Volumina UND Konzentrationen).

Dieses Modul rechnet die Konzentrationen in Volumina um, basierend auf:
- Gesamt-Volumen der Probe (z.B. 1000 µL)
- Konzentration jedes Reagenz
- Volumen = (Konzentration × Gesamt-Volumen) / Konzentration_max
"""
from __future__ import annotations
import logging

logger = logging.getLogger("caste.reagent_converter")

# Gesamt-Volumen der Probe in µL
DEFAULT_TOTAL_VOLUME_UL = 1000.0

# Reagenzien-Konfiguration
REAGENT_CONFIG = {
    "ascorbic_acid": {
        "concentration_key": "ascorbic_acid_concentration_mm",
        "default_volume_ul": 500.0,
        "min_volume_ul": 50.0,
        "max_volume_ul": 2000.0,
    },
    "fecl3": {
        "concentration_key": "fecl3_concentration_mm",
        "default_volume_ul": 100.0,
        "min_volume_ul": 10.0,
        "max_volume_ul": 500.0,
    },
    "h2o2": {
        "concentration_key": "h2o2_concentration_mm",
        "default_volume_ul": 200.0,
        "min_volume_ul": 20.0,
        "max_volume_ul": 1000.0,
    },
    "fluorescein": {
        "concentration_key": "fluorescein_concentration_mm",
        "default_volume_ul": 100.0,
        "min_volume_ul": 10.0,
        "max_volume_ul": 500.0,
    },
    "phosphate_buffer": {
        "concentration_key": "phosphate_buffer_concentration_mm",
        "default_volume_ul": 100.0,
        "min_volume_ul": 50.0,
        "max_volume_ul": 2000.0,
    },
}


def convert_concentrations_to_reagents(
    parameters: dict,
    total_volume_ul: float = DEFAULT_TOTAL_VOLUME_UL,
) -> list[dict]:
    """
    Rechnet die Konzentrationen in Reagenzien (Volumina + Konzentrationen) um.
    
    Args:
        parameters: Die Parameter aus dem experiment_profile.yaml.
        total_volume_ul: Das Gesamt-Volumen der Probe in µL.
    
    Returns:
        Eine Liste von Reagenzien-Dictionaries, jedes mit:
        - reagent_name: Der Name des Reagenz.
        - volume_ul: Das Volumen in µL.
        - concentration_mm: Die Konzentration in mM.
    """
    reagents = []
    
    for reagent_name, config in REAGENT_CONFIG.items():
        concentration_key = config["concentration_key"]
        
        # Konzentration aus den Parametern lesen
        concentration_mm = parameters.get(concentration_key)
        
        if concentration_mm is None:
            # Fallback: Standard-Volumen verwenden
            volume_ul = config["default_volume_ul"]
            concentration_mm = 1.0  # Default-Konzentration
            logger.warning(
                "Parameter %s not found - using default volume %.1f µL",
                concentration_key, volume_ul,
            )
        else:
            # Volumen berechnen: proportional zur Konzentration
            # Vereinfachte Formel: Volumen = Default-Volumen × (Konzentration / Default-Konzentration)
            # Default-Konzentration ist 1.0 mM
            volume_ul = config["default_volume_ul"] * (concentration_mm / 1.0)
            
            # Volumen auf [min, max] kappen
            volume_ul = max(config["min_volume_ul"], min(config["max_volume_ul"], volume_ul))
        
        reagents.append({
            "reagent_name": reagent_name,
            "volume_ul": round(volume_ul, 2),
            "concentration_mm": round(concentration_mm, 4),
        })
    
    # Gesamt-Volumen prüfen
    total = sum(r["volume_ul"] for r in reagents)
    if total > total_volume_ul:
        logger.warning(
            "Total volume %.1f µL exceeds maximum %.1f µL - scaling down",
            total, total_volume_ul,
        )
        # Skalieren: Alle Volumina proportional reduzieren
        scale_factor = total_volume_ul / total
        for reagent in reagents:
            reagent["volume_ul"] = round(reagent["volume_ul"] * scale_factor, 2)
    
    return reagents

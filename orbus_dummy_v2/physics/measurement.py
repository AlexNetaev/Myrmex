"""
Station 2: Measurement (Reaction + Fluorescence).
In Phase 1: Erzeugt eine einfache Zeitreihe mit Rauschen.
"""
from .base_physics import BasePhysics
from ..models.experiment import MeasurementResult
import math


class MeasurementPhysics(BasePhysics):
    """
    Simuliert die Measurement-Station.
    
    In Phase 1: Einfache exponentielle Kurve mit Rauschen.
    Später: Komplexere Kinetik, multiple Reaktionen, etc.
    """
    
    def simulate(self, params: dict) -> list[MeasurementResult]:
        """
        Simuliert die Measurement-Zeitreihe.
        
        Args:
            params: measurement_params aus ExperimentJob.
        
        Returns:
            Liste von MeasurementResult-Objekten.
        """
        duration_s = params.get("duration_s", 60.0)
        interval_ms = params.get("interval_ms", 1000)
        target_temp_c = params.get("target_temperature_c", 25.0)
        
        # Zeitpunkte generieren
        num_points = int((duration_s * 1000) / interval_ms) + 1
        results = []
        
        for i in range(num_points):
            time_ms = i * interval_ms
            time_s = time_ms / 1000.0
            
            # Einfache exponentielle Annäherung an Ziel-Temperatur
            # T(t) = T_start + (T_target - T_start) * (1 - exp(-t/tau))
            t_start = 20.0  # Raumtemperatur
            tau = 30.0  # Zeitkonstante in Sekunden
            temp_c = t_start + (target_temp_c - t_start) * (1 - math.exp(-time_s / tau))
            
            # Fluoreszenz: Einfache lineare Abnahme mit Rauschen
            # (simuliert z.B. Quenching oder Photobleaching)
            base_fluorescence = 100.0
            decay_rate = 0.5  # AU pro Sekunde
            fluorescence_au = base_fluorescence - (decay_rate * time_s)
            
            # Rauschen hinzufügen
            noise = self.rng.normal(0, 2.0)  # Normalverteilung, sigma=2
            fluorescence_au += noise
            
            # Sicherstellen, dass Fluoreszenz nicht negativ wird
            fluorescence_au = max(0.0, fluorescence_au)
            
            results.append(MeasurementResult(
                time_ms=time_ms,
                temp_c=round(temp_c, 2),
                fluorescence_au=round(fluorescence_au, 2)
            ))
        
        return results

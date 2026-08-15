"""
Station 1: Preparation (Dosing + Mixing).
In Phase 1: Validiert nur die Parameter und gibt Status zurück.
"""
from .base_physics import BasePhysics


class PreparationPhysics(BasePhysics):
    """
    Simuliert die Preparation-Station.
    
    In Phase 1: Minimalistisch - validiert nur Parameter.
    Später: Kann Dosier-Ungenauigkeiten, Misch-Effekte, etc. simulieren.
    """
    
    def simulate(self, params: dict) -> dict:
        """
        Simuliert die Preparation.
        
        Args:
            params: preparation_params aus ExperimentJob.
        
        Returns:
            dict mit status und optionalen Metadaten.
        """
        # In Phase 1: Nur validieren, keine echte Simulation
        reagents = params.get("reagents", [])
        mixing_time_s = params.get("mixing_time_s", 10.0)
        
        # Einfache Validierung
        if not reagents:
            return {"status": "ERROR", "message": "No reagents specified"}
        
        if mixing_time_s <= 0:
            return {"status": "ERROR", "message": "Invalid mixing time"}
        
        # Success
        return {
            "status": "OK",
            "reagents_count": len(reagents),
            "mixing_time_s": mixing_time_s,
            "metadata": {
                "station": "preparation",
                "phase": "minimal_dummy"
            }
        }

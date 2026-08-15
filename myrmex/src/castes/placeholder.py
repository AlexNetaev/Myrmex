"""
src/castes/placeholder.py
Eine minimale Beispiel-Kaste für Tests und Demonstration.

Diese Kaste tut nichts Echtes — sie liest ein Pheromon, schreibt ein neues,
und gibt ein Ergebnis zurück. Dient als Template für echte Kasten.
"""
from __future__ import annotations
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


class PlaceholderCaste(BaseCaste):
    """
    Minimale Beispiel-Kaste.
    
    Liest TRAIL-Pheromone, schreibt ein neues TRAIL-Pheromon.
    Keine echte Logik — dient nur als Template.
    """
    
    caste_name = CasteName.ANALYST  # Beispiel: als Analyst tunken
    role = "Platzhalter"
    specialization = "Keine echte Spezialisierung"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Minimale Ausführung: Liest Trails, schreibt einen neuen.
        """
        # 1. Trails lesen
        trails = self.read_pheromones(pheromone_type=PheromoneType.TRAIL)
        pheromones_read = len(trails)
        
        # 2. Etwas "tun" (Platzhalter)
        # In echten Kasten: LLM-Aufrufe, Datenanalyse, etc.
        
        # 3. Neues Pheromon schreiben
        new_pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=f"Placeholder output: read {pheromones_read} trails",
            tags=["placeholder", "example"],
            strength=0.4,
            relevance=0.5,
        )
        
        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=pheromones_read,
            pheromones_written=1,
            output_files=[],
            extra_data={
                "new_pheromone_id": new_pheromone.id,
                "trails_read_ids": [t.id for t in trails],
            },
        )

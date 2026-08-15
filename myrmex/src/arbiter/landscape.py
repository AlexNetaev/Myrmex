"""
src/arbiter/landscape.py
Analysiert die Pheromon-Landschaft und erzeugt eine LandscapeSummary.
"""
from __future__ import annotations
from src.pheromones.pheromone_field import PheromoneField
from src.models.landscape import LandscapeSummary
from src.models.pheromone import PheromoneType
import config


class LandscapeAnalyzer:
    """
    Liest die Pheromon-Landschaft und erzeugt eine kompakte Zusammenfassung.
    
    Der Arbiter nutzt diese Zusammenfassung, um Entscheidungen zu treffen,
    ohne jedes Pheromon einzeln betrachten zu müssen.
    """
    
    def __init__(self, pheromone_field: PheromoneField) -> None:
        self.field = pheromone_field
    
    def analyze(self) -> LandscapeSummary:
        """
        Analysiert die aktuelle Pheromon-Landschaft und gibt eine
        LandscapeSummary zurück.
        
        Returns:
            Eine LandscapeSummary mit allen relevanten Metriken.
        """
        # Alle Pheromone scannen (ohne Filter, um die Gesamtsicht zu haben)
        all_pheromones = self.field.scan()
        
        # Nach Typ gruppieren
        trails = [p for p in all_pheromones if p.type == PheromoneType.TRAIL]
        crystals = [p for p in all_pheromones if p.type == PheromoneType.CRYSTAL]
        warnings = [p for p in all_pheromones if p.type == PheromoneType.WARNING]
        
        # Stärken berechnen
        effective_strengths = [p.effective_strength() for p in all_pheromones]
        total_strength = sum(effective_strengths)
        avg_strength = total_strength / len(effective_strengths) if effective_strengths else 0.0
        max_strength = max(effective_strengths) if effective_strengths else 0.0
        
        # Dichte-Metriken
        is_sparse = self._check_is_sparse(trails, crystals, warnings)
        has_strong_trail = self._check_has_strong_trail(trails)
        has_warning_nearby = self._check_has_warning_nearby(warnings)
        
        # Stärkster Trail und stärkste Warnung
        strongest_trail = self._find_strongest(trails)
        strongest_warning = self._find_strongest(warnings)
        
        return LandscapeSummary(
            trail_count=len(trails),
            crystal_count=len(crystals),
            warning_count=len(warnings),
            total_count=len(all_pheromones),
            total_effective_strength=total_strength,
            average_effective_strength=avg_strength,
            max_effective_strength=max_strength,
            is_sparse=is_sparse,
            has_strong_trail=has_strong_trail,
            has_warning_nearby=has_warning_nearby,
            strongest_trail_id=strongest_trail.id if strongest_trail else None,
            strongest_warning_id=strongest_warning.id if strongest_warning else None,
        )
    
    def _check_is_sparse(self, trails, crystals, warnings) -> bool:
        """
        Prüft, ob die Landschaft 'dünn' ist.
        
        Eine Landschaft gilt als dünn, wenn:
        - Weniger als SPARSE_TRAIL_THRESHOLD Trails existieren, UND
        - Weniger als SPARSE_CRYSTAL_THRESHOLD Kristalle existieren
        
        Dies ist der Zustand, in dem der Arbiter EXPLORE wählen sollte
        (Basismessungen, OFAT-Scans), um die Landschaft zu erkunden.
        """
        SPARSE_TRAIL_THRESHOLD = 3
        SPARSE_CRYSTAL_THRESHOLD = 1
        
        return len(trails) < SPARSE_TRAIL_THRESHOLD and len(crystals) < SPARSE_CRYSTAL_THRESHOLD
    
    def _check_has_strong_trail(self, trails) -> bool:
        """
        Prüft, ob es einen starken Trail gibt, der zum Ziel führen könnte.
        
        Ein Trail gilt als stark, wenn seine effective_strength() >= STRONG_TRAIL_THRESHOLD.
        Dies ist der Zustand, in dem der Arbiter FOLLOW_TRAIL wählen sollte.
        """
        STRONG_TRAIL_THRESHOLD = 0.5
        
        return any(p.effective_strength() >= STRONG_TRAIL_THRESHOLD for p in trails)
    
    def _check_has_warning_nearby(self, warnings) -> bool:
        """
        Prüft, ob es Warnungen gibt, die den Weg blockieren könnten.
        
        Eine Warnung gilt als relevant, wenn ihre effective_strength() >= WARNING_THRESHOLD.
        Dies ist der Zustand, in dem der Arbiter DETOUR wählen sollte.
        """
        WARNING_THRESHOLD = 0.3
        
        return any(p.effective_strength() >= WARNING_THRESHOLD for p in warnings)
    
    def _find_strongest(self, pheromones):
        """
        Findet das Pheromon mit der höchsten effective_strength().
        
        Returns:
            Das stärkste Pheromon, oder None wenn die Liste leer ist.
        """
        if not pheromones:
            return None
        return max(pheromones, key=lambda p: p.effective_strength())

"""
src/arbiter/decision.py
Trifft die eigentliche Entscheidung basierend auf der Landschaft.
"""
from __future__ import annotations
from src.models.landscape import LandscapeSummary
from src.models.arbiter import ArbiterActionType, ArbiterPlan
from src.models.directive import TargetCrystal
from src.models.loop import LoopName


class DecisionEngine:
    """
    Trifft die Entscheidung, welche Aktion als nächstes ausgeführt wird.
    
    Die Entscheidung basiert auf der LandscapeSummary und dem Ziel-Kristall.
    Sie ist rein deterministisch — keine LLM-Aufrufe.
    """
    
    def decide(
        self,
        landscape: LandscapeSummary,
        target_crystal: TargetCrystal | None,
        current_plan: ArbiterPlan | None,
    ) -> tuple[ArbiterActionType, str, list[LoopName]]:
        """
        Entscheidet die nächste Aktion basierend auf der Landschaft.
        
        Args:
            landscape: Die aktuelle LandscapeSummary.
            target_crystal: Der Ziel-Kristall, oder None wenn keiner definiert ist.
            current_plan: Der aktuelle Plan (für Kontext), oder None wenn keiner existiert.
        
        Returns:
            Ein Tuple von (ArbiterActionType, Reasoning, LoopPriorities).
        """
        # Wenn der Ziel-Kristall bereits erreicht ist, konsolidieren
        if target_crystal is not None and target_crystal.achieved:
            return (
                ArbiterActionType.CONSOLIDATE,
                "Target crystal is already achieved. Consolidating findings and archiving.",
                self._default_loop_priorities(),
            )
        
        # Wenn es Warnungen gibt, ausweichen
        if landscape.has_warning_nearby:
            return (
                ArbiterActionType.DETOUR,
                f"Warning detected (strongest: {landscape.strongest_warning_id}). "
                f"Taking a detour to avoid the blocked path.",
                self._detour_loop_priorities(),
            )
        
        # Wenn es einen starken Trail gibt, folgen (PRIORITÄT VOR EXPLORE!)
        if landscape.has_strong_trail:
            return (
                ArbiterActionType.FOLLOW_TRAIL,
                f"Strong trail detected ({landscape.strongest_trail_id}). "
                f"Following it towards the target crystal.",
                self._follow_trail_loop_priorities(),
            )
        
        # Wenn die Landschaft dünn ist UND keine klare Richtung existiert, erkunden
        if landscape.is_sparse:
            return (
                ArbiterActionType.EXPLORE,
                f"Landscape is sparse ({landscape.trail_count} trails, "
                f"{landscape.crystal_count} crystals). Exploring to gather more data.",
                self._explore_loop_priorities(),
            )
        
        # Default: Konsolidieren (mehr Messungen zum Verifizieren)
        return (
            ArbiterActionType.CONSOLIDATE,
            "Landscape is moderate but no clear path to target. "
            "Consolidating with additional measurements.",
            self._default_loop_priorities(),
        )
    
    def _default_loop_priorities(self) -> list[LoopName]:
        """Standard-Priorisierung der Schleifen."""
        return [
            LoopName.LOOP_B_EXPERIMENT,
            LoopName.LOOP_A_SIMULATION,
            LoopName.LOOP_C_KNOWLEDGE,
            LoopName.LOOP_D_COORDINATION,
        ]
    
    def _explore_loop_priorities(self) -> list[LoopName]:
        """Priorisierung für EXPLORE (Basismessungen)."""
        return [
            LoopName.LOOP_B_EXPERIMENT,    # Erst messen
            LoopName.LOOP_A_SIMULATION,    # Dann simulieren
            LoopName.LOOP_C_KNOWLEDGE,     # Dann Wissen aufbauen
            LoopName.LOOP_D_COORDINATION,
        ]
    
    def _follow_trail_loop_priorities(self) -> list[LoopName]:
        """Priorisierung für FOLLOW_TRAIL (gezielte Optimierung)."""
        return [
            LoopName.LOOP_B_EXPERIMENT,    # Dem Trail folgen
            LoopName.LOOP_A_SIMULATION,
            LoopName.LOOP_C_KNOWLEDGE,
            LoopName.LOOP_D_COORDINATION,
        ]
    
    def _detour_loop_priorities(self) -> list[LoopName]:
        """Priorisierung für DETOUR (Warnung ausweichen)."""
        return [
            LoopName.LOOP_A_SIMULATION,    # Erst simulieren (sicher)
            LoopName.LOOP_C_KNOWLEDGE,     # Dann Wissen konsolidieren
            LoopName.LOOP_B_EXPERIMENT,    # Dann vorsichtig messen
            LoopName.LOOP_D_COORDINATION,
        ]

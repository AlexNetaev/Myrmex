"""
Myrmex - Haupt-Einstiegspunkt.

Führt die vollständige Myrmex-Schleife aus:
1. Initialisiert den Workspace.
2. Initialisiert das Pheromon-Feld.
3. Initialisiert den LoopRunner und den Arbiter.
4. Führt mehrere Zyklen aus.
5. Schreibt die Ergebnisse.
"""
from __future__ import annotations
import logging
from pathlib import Path

from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner
from src.pheromones.pheromone_field import PheromoneField
from src.workspace.workspace_manager import WorkspaceManager

logger = logging.getLogger("myrmex.main")


def run_myrmex(
    workspace_path: Path | None = None,
    max_cycles: int = 5,
) -> None:
    """
    Führt die vollständige Myrmex-Schleife aus.
    
    Args:
        workspace_path: Der Pfad zum Workspace. Defaults to config.WORKSPACE_ROOT.
        max_cycles: Die maximale Anzahl der Zyklen.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    logger.info("Myrmex starting up.")
    
    # 1. Workspace initialisieren
    workspace_manager = WorkspaceManager(workspace_root=workspace_path)
    workspace_manager.initialize()
    workspace = workspace_manager.workspace_root
    
    # 2. Pheromon-Feld initialisieren
    pheromone_field = PheromoneField(field_root=workspace / "01_Pheromon_Field")
    
    # 3. LoopRunner und Arbiter initialisieren
    loop_runner = LoopRunner(workspace_path=workspace)
    arbiter = Arbiter(workspace_path=workspace)
    
    # 4. Zyklen ausführen
    for cycle_num in range(1, max_cycles + 1):
        logger.info("=" * 70)
        logger.info("Starting Myrmex cycle #%d", cycle_num)
        logger.info("=" * 70)
        
        # Arbiter-Zyklus ausführen
        cycle_result = arbiter.run_cycle(loop_runner)
        
        logger.info(
            "[Cycle #%d] Action: %s | Loop: %s | Reasoning: %s",
            cycle_num,
            cycle_result.action.value,
            cycle_result.loop_name.value,
            cycle_result.reasoning,
        )
        
        # Pheromon-Feld verdunsten lassen
        evaporation_result = pheromone_field.evaporate()
        logger.info(
            "[Cycle #%d] Evaporation: %d trails evaporated, %d remaining",
            cycle_num,
            evaporation_result.trails_evaporated,
            evaporation_result.trails_remaining,
        )
    
    logger.info("Myrmex complete.")


if __name__ == "__main__":
    run_myrmex()
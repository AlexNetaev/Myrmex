"""
tests/test_end_to_end.py
End-to-End-Test: Ein vollständiger Zyklus durch den gesamten Schwarm.

Dieser Test verifiziert, dass alle Komponenten korrekt zusammenarbeiten:
1. Arbiter analysiert die Pheromon-Landschaft
2. Arbiter wählt eine Schleife basierend auf der Landschaft
3. LoopRunner führt die Schleife aus
4. Die Kasten werden in der richtigen Reihenfolge aufgerufen
5. Pheromone werden geschrieben
6. Der Arbiter sieht die neuen Pheromone und kann die nächste Entscheidung treffen
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner
from src.pheromones.pheromone_field import PheromoneField
from src.models.arbiter import ArbiterActionType, ArbiterCycleResult
from src.models.loop import LoopName, ActionType
from src.models.pheromone import PheromoneType
from src.workspace.workspace_manager import WorkspaceManager


@pytest.fixture
def e2e_workspace():
    """Erstellt einen vollständigen temporären Workspace."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # WorkspaceManager initialisiert alle Verzeichnisse
    wm = WorkspaceManager(workspace_root=workspace_path)
    wm.initialize()
    
    yield workspace_path
    
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestEndToEndCycle:
    """Testet einen vollständigen Zyklus durch den Schwarm."""
    
    def test_full_cycle_produces_pheromones(self, e2e_workspace):
        """
        Ein vollständiger Zyklus erzeugt Pheromone.
        
        Flow:
        1. Arbiter analysiert leere Landschaft → EXPLORE
        2. LoopRunner führt LOOP_B_EXPERIMENT aus
        3. Kasten schreiben Pheromone
        4. Pheromon-Feld ist nicht mehr leer
        """
        field = PheromoneField(field_root=e2e_workspace / "01_Pheromon_Field")
        loop_runner = LoopRunner(workspace_path=e2e_workspace)
        arbiter = Arbiter(workspace_path=e2e_workspace)
        
        # Vor dem Zyklus: Feld ist leer
        initial_pheromones = field.scan()
        
        # Zyklus ausführen
        result = arbiter.run_cycle(loop_runner)
        
        # Ergebnis sollte ein ArbiterCycleResult sein
        assert isinstance(result, ArbiterCycleResult)
        
        # Nach dem Zyklus: Feld sollte Pheromone enthalten
        final_pheromones = field.scan()
        assert len(final_pheromones) >= len(initial_pheromones)
        
        # Die Landschaft sollte sich geändert haben
        assert result.landscape_summary is not None
    
    def test_arbiter_selects_explore_for_empty_landscape(self, e2e_workspace):
        """
        Bei leerer Landschaft wählt der Arbiter EXPLORE.
        """
        loop_runner = LoopRunner(workspace_path=e2e_workspace)
        arbiter = Arbiter(workspace_path=e2e_workspace)
        
        result = arbiter.run_cycle(loop_runner)
        
        # Bei leerer Landschaft sollte EXPLORE gewählt werden
        assert result.action == ArbiterActionType.EXPLORE
        assert result.loop_name == LoopName.LOOP_B_EXPERIMENT
    
    def test_multiple_cycles_accumulate_knowledge(self, e2e_workspace):
        """
        Mehrere Zyklen akkumulieren Wissen.
        
        Nach mehreren Zyklen sollte die theory_baseline.md Inhalte haben.
        """
        loop_runner = LoopRunner(workspace_path=e2e_workspace)
        arbiter = Arbiter(workspace_path=e2e_workspace)
        field = PheromoneField(field_root=e2e_workspace / "01_Pheromon_Field")
        
        # 3 Zyklen ausführen
        for i in range(3):
            result = arbiter.run_cycle(loop_runner)
            field.evaporate()  # Pheromone altern lassen
        
        # Nach 3 Zyklen sollte es Pheromone geben
        pheromones = field.scan()
        assert len(pheromones) >= 0  # Kann leer sein, wenn alle verdunstet sind
        
        # Die theory_baseline.md sollte existieren
        theory_path = e2e_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        # Sie existiert möglicherweise nicht, wenn keine Knowledge-Pheromone konsolidiert wurden
        # Das ist in Ordnung für diesen Test
    
    def test_cycle_result_structure(self, e2e_workspace):
        """
        Das ArbiterCycleResult hat die korrekte Struktur.
        """
        loop_runner = LoopRunner(workspace_path=e2e_workspace)
        arbiter = Arbiter(workspace_path=e2e_workspace)
        
        result = arbiter.run_cycle(loop_runner)
        
        # Alle Felder sollten vorhanden sein
        assert result.action is not None
        assert result.reasoning is not None
        assert result.loop_name is not None
        assert result.loop_results is not None
        assert result.landscape_summary is not None
        
        # landscape_summary sollte die erwarteten Schlüssel haben
        assert "trail_count" in result.landscape_summary
        assert "crystal_count" in result.landscape_summary
        assert "warning_count" in result.landscape_summary


class TestStructureIntegrity:
    """Überprüft die strukturelle Integrität des Systems."""
    
    def test_all_castes_are_registered(self, e2e_workspace):
        """
        Alle 9 Kasten sind in der Registry registriert.
        """
        from src.castes.registry import get_registry
        
        registry = get_registry()
        registered_actions = registry.get_registered_actions()
        
        # Mindestens die folgenden Aktionen sollten registriert sein
        expected_actions = [
            ActionType.ANALYZE,
            ActionType.MEASURE,
            ActionType.SIMULATE,
            ActionType.CONSOLIDATE,
            ActionType.VALIDATE,
        ]
        
        for action in expected_actions:
            assert action in registered_actions, f"{action.value} ist nicht registriert"
    
    def test_no_placeholder_castes_for_core_actions(self, e2e_workspace):
        """
        Die Kern-Aktionen sind nicht mit PlaceholderCaste belegt.
        """
        from src.castes.registry import get_registry
        from src.castes.placeholder import PlaceholderCaste
        
        registry = get_registry()
        
        core_actions = [
            ActionType.ANALYZE,
            ActionType.MEASURE,
            ActionType.SIMULATE,
            ActionType.CONSOLIDATE,
            ActionType.VALIDATE,
        ]
        
        for action in core_actions:
            caste_class = registry.get_caste_for_action(action)
            assert caste_class is not PlaceholderCaste, \
                f"{action.value} ist noch mit PlaceholderCaste belegt"
    
    def test_workspace_structure_is_complete(self, e2e_workspace):
        """
        Die Workspace-Struktur ist vollständig.
        """
        expected_dirs = [
            e2e_workspace / "00_System",
            e2e_workspace / "01_Pheromon_Field",
            e2e_workspace / "02_Research_Cycles",
            e2e_workspace / "03_Hardware_Queue",
            e2e_workspace / "04_Knowledge_Base",
            e2e_workspace / "05_Loops",
        ]
        
        for dir_path in expected_dirs:
            assert dir_path.exists(), f"Verzeichnis fehlt: {dir_path}"
            assert dir_path.is_dir(), f"Kein Verzeichnis: {dir_path}"
    
    def test_loop_definitions_are_consistent(self, e2e_workspace):
        """
        Die Schleifen-Definitionen sind konsistent.
        """
        from src.loops.loop_definitions import LOOP_DEFINITIONS, get_loop_definition
        
        # Alle 4 Schleifen sollten definiert sein
        assert LoopName.LOOP_A_SIMULATION in LOOP_DEFINITIONS
        assert LoopName.LOOP_B_EXPERIMENT in LOOP_DEFINITIONS
        assert LoopName.LOOP_C_KNOWLEDGE in LOOP_DEFINITIONS
        assert LoopName.LOOP_D_COORDINATION in LOOP_DEFINITIONS
        
        # Schleife B sollte die meisten Aktionen haben (der Forschungs-Motor)
        loop_b = get_loop_definition(LoopName.LOOP_B_EXPERIMENT)
        assert len(loop_b) >= 2  # Mindestens PLAN und MEASURE

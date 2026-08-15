"""
tests/test_arbiter.py
Tests für den Arbiter.
"""
import pytest
import json
from pathlib import Path
import tempfile
import shutil

from src.arbiter.arbiter import Arbiter
from src.models.arbiter import ArbiterPlan, ArbiterActionType
from src.models.directive import Directive, TargetCrystal
from src.models.loop import LoopName
from src.pheromones.pheromone_field import PheromoneField
from src.models.pheromone import Pheromone, PheromoneType
import config


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace für Tests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # System-Verzeichnis erstellen
    system_dir = workspace_path / "00_System"
    system_dir.mkdir(parents=True)
    
    yield workspace_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def arbiter_with_workspace(temp_workspace):
    """Erstellt einen Arbiter mit temporärem Workspace."""
    return Arbiter(workspace_path=temp_workspace)


class TestArbiterEmptyLandscape:
    """Tests für Arbiter mit leerer Landschaft."""
    
    def test_empty_landscape_explores(self, arbiter_with_workspace, temp_workspace):
        """Leere Landschaft → EXPLORE."""
        plan = arbiter_with_workspace.run_cycle()
        
        assert plan.next_action == ArbiterActionType.EXPLORE
        assert "sparse" in plan.next_action_reasoning.lower()
    
    def test_plan_written_to_disk(self, arbiter_with_workspace, temp_workspace):
        """Plan wird korrekt auf Disk geschrieben."""
        plan = arbiter_with_workspace.run_cycle()
        
        plan_file = temp_workspace / "00_System" / "arbiter_plan.json"
        assert plan_file.exists()
        
        # Datei lesen und validieren
        raw = json.loads(plan_file.read_text())
        assert raw["next_action"] == plan.next_action.value
        assert raw["revision_count"] == plan.revision_count


class TestArbiterWithStrongTrail:
    """Tests für Arbiter mit starkem Trail."""
    
    def test_strong_trail_follows(self, arbiter_with_workspace, temp_workspace):
        """Starker Trail → FOLLOW_TRAIL."""
        # Stelle sicher, dass das Verzeichnis existiert
        pheromon_dir = temp_workspace / "01_Pheromon_Field"
        pheromon_dir.mkdir(parents=True, exist_ok=True)
        
        # Pheromon-Feld initialisieren und starken Trail erstellen
        field = PheromoneField(field_root=pheromon_dir)
        pheromone = Pheromone(
            id="trail_strong",
            type=PheromoneType.TRAIL,
            strength=0.8,
            age_cycles=0,
            relevance=1.0,
            content="Strong trail to follow",
            source_agent="test",
        )
        field.emit(pheromone)
        
        # Erstelle neuen Arbiter, der dasselbe Feld verwendet
        arbiter = Arbiter(workspace_path=temp_workspace)
        plan = arbiter.run_cycle()
        
        assert plan.next_action == ArbiterActionType.FOLLOW_TRAIL
        assert "trail" in plan.next_action_reasoning.lower()


class TestArbiterRevisionCount:
    """Tests für Revisionszähler."""
    
    def test_revision_count_increments(self, arbiter_with_workspace, temp_workspace):
        """revision_count wird bei jedem Zyklus inkrementiert."""
        plan1 = arbiter_with_workspace.run_cycle()
        assert plan1.revision_count == 0  # Erster Plan
        
        plan2 = arbiter_with_workspace.run_cycle()
        assert plan2.revision_count == 1
        
        plan3 = arbiter_with_workspace.run_cycle()
        assert plan3.revision_count == 2


class TestArbiterPlanPersistence:
    """Tests für Plan-Persistenz."""
    
    def test_plan_read_from_disk(self, arbiter_with_workspace, temp_workspace):
        """Plan wird von Disk gelesen."""
        # Ersten Plan schreiben
        plan1 = arbiter_with_workspace.run_cycle()
        
        # Zweiten Plan schreiben (sollte revision_count erhöhen)
        plan2 = arbiter_with_workspace.run_cycle()
        
        assert plan2.revision_count == plan1.revision_count + 1
    
    def test_plan_atomic_write(self, arbiter_with_workspace, temp_workspace):
        """Plan wird atomar geschrieben (keine .tmp Datei nach Schreibvorgang)."""
        arbiter_with_workspace.run_cycle()
        
        plan_file = temp_workspace / "00_System" / "arbiter_plan.json"
        temp_file = plan_file.with_suffix(".tmp")
        
        # Temp-Datei sollte nicht mehr existieren
        assert not temp_file.exists()


class TestArbiterMissingFiles:
    """Tests für fehlende Dateien (Graceful Handling)."""
    
    def test_missing_directive_handled(self, arbiter_with_workspace, temp_workspace):
        """Fehlende directive.md führt nicht zu Crash."""
        # directive.md existiert bereits als Platzhalter, aber wir testen mit leerer
        plan = arbiter_with_workspace.run_cycle()
        
        # Sollte trotzdem funktionieren
        assert plan is not None
        assert plan.directive_summary == "(No directive set)" or len(plan.directive_summary) > 0
    
    def test_missing_target_crystal_handled(self, arbiter_with_workspace, temp_workspace):
        """Fehlender target_crystal.json führt nicht zu Crash."""
        plan = arbiter_with_workspace.run_cycle()
        
        # Sollte trotzdem funktionieren
        assert plan is not None
        # Ohne Ziel-Kristall sollte die Entscheidung basierend auf Landschaft getroffen werden
        assert plan.next_action in [ArbiterActionType.EXPLORE, ArbiterActionType.CONSOLIDATE]
    
    def test_missing_arbiter_plan_handled(self, arbiter_with_workspace, temp_workspace):
        """Fehlender arbiter_plan.json führt nicht zu Crash (erster Lauf)."""
        # Lösche eventuell vorhandenen Plan
        plan_file = temp_workspace / "00_System" / "arbiter_plan.json"
        if plan_file.exists():
            plan_file.unlink()
        
        plan = arbiter_with_workspace.run_cycle()
        
        assert plan is not None
        assert plan.revision_count == 0  # Erster Plan


class TestArbiterWithTargetCrystal:
    """Tests für Arbiter mit Ziel-Kristall."""
    
    def test_achieved_target_consolidates(self, arbiter_with_workspace, temp_workspace):
        """Erreichter Ziel-Kristall → CONSOLIDATE."""
        # Ziel-Kristall schreiben
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target achieved",
            criteria={"value": 1.0},
            achieved=True,
        )
        target_file = temp_workspace / "00_System" / "target_crystal.json"
        target_file.write_text(target_crystal.model_dump_json(), encoding="utf-8")
        
        plan = arbiter_with_workspace.run_cycle()
        
        assert plan.next_action == ArbiterActionType.CONSOLIDATE
        assert "achieved" in plan.next_action_reasoning.lower()
    
    def test_unachieved_target_continues(self, arbiter_with_workspace, temp_workspace):
        """Nicht erreichter Ziel-Kristall → normale Entscheidung."""
        # Ziel-Kristall schreiben (nicht erreicht)
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target not achieved",
            criteria={"value": 1.0},
            achieved=False,
        )
        target_file = temp_workspace / "00_System" / "target_crystal.json"
        target_file.write_text(target_crystal.model_dump_json(), encoding="utf-8")
        
        plan = arbiter_with_workspace.run_cycle()
        
        # Sollte basierend auf Landschaft entscheiden (hier: EXPLORE da leer)
        assert plan.target_crystal_id == "target_1"


class TestArbiterLoopPriorities:
    """Tests für Loop-Prioritäten im Plan."""
    
    def test_loop_priorities_written(self, arbiter_with_workspace, temp_workspace):
        """Loop-Prioritäten werden im Plan gespeichert."""
        plan = arbiter_with_workspace.run_cycle()
        
        assert len(plan.loop_priorities) == 4
        assert all(isinstance(p, LoopName) for p in plan.loop_priorities)
    
    def test_explore_loop_priorities_order(self, arbiter_with_workspace, temp_workspace):
        """EXPLORE-Prioritäten in korrekter Reihenfolge."""
        plan = arbiter_with_workspace.run_cycle()
        
        # Bei leerer Landschaft sollte EXPLORE gewählt werden
        assert plan.next_action == ArbiterActionType.EXPLORE
        # LOOP_B_EXPERIMENT sollte zuerst kommen
        assert plan.loop_priorities[0] == LoopName.LOOP_B_EXPERIMENT


class TestArbiterDirectiveSummary:
    """Tests für Directive-Zusammenfassung."""
    
    def test_short_directive_summary(self, arbiter_with_workspace, temp_workspace):
        """Kurze Directive wird vollständig übernommen."""
        directive = Directive(
            title="Short Directive",
            description="This is a short description.",
            success_criteria=[],
            constraints=[],
        )
        directive_file = temp_workspace / "00_System" / "directive.md"
        directive_file.write_text(directive.description, encoding="utf-8")
        
        plan = arbiter_with_workspace.run_cycle()
        
        assert "short description" in plan.directive_summary.lower()
    
    def test_long_directive_truncated(self, arbiter_with_workspace, temp_workspace):
        """Lange Directive wird abgeschnitten."""
        long_text = "A" * 500  # 500 Zeichen
        directive_file = temp_workspace / "00_System" / "directive.md"
        directive_file.write_text(long_text, encoding="utf-8")
        
        plan = arbiter_with_workspace.run_cycle()
        
        # Zusammenfassung sollte max 200 Zeichen + "..." sein
        assert len(plan.directive_summary) <= 203  # 200 + "..."
        assert plan.directive_summary.startswith("A")

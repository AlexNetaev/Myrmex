"""
tests/test_base_caste.py
Tests für die BaseCaste-Klasse und PlaceholderCaste.
"""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from src.castes.base_caste import BaseCaste
from src.castes.placeholder import PlaceholderCaste
from src.models.caste import CasteName, CasteExecutionResult
from src.models.pheromone import Pheromone, PheromoneType
from src.pheromones.pheromone_field import PheromoneField
import config


class TestBaseCaste:
    """Tests für die BaseCaste-Klasse."""
    
    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        """Erstellt einen temporären Workspace."""
        ws = tmp_path / "test_workspace"
        ws.mkdir()
        # Verzeichnisse erstellen
        (ws / "00_System").mkdir()
        (ws / "01_Pheromon_Field").mkdir()
        (ws / "01_Pheromon_Field" / "trails").mkdir()
        (ws / "01_Pheromon_Field" / "crystals").mkdir()
        (ws / "01_Pheromon_Field" / "warnings").mkdir()
        (ws / "04_Knowledge_Base").mkdir()
        return ws
    
    @pytest.fixture
    def directive_file(self, workspace: Path) -> Path:
        """Erstellt eine directive.md."""
        directive = workspace / "00_System" / "directive.md"
        directive.write_text("# Test Directive\n\nDies ist ein Test.", encoding="utf-8")
        return directive
    
    @pytest.fixture
    def theory_file(self, workspace: Path) -> Path:
        """Erstellt eine theory_baseline.md."""
        theory = workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory.write_text("# Theory Baseline\n\nNoch keine Erkenntnisse.", encoding="utf-8")
        return theory
    
    def test_read_directive_exists(self, workspace: Path, directive_file: Path):
        """read_directive() liest directive.md korrekt."""
        caste = PlaceholderCaste(workspace_path=workspace)
        text = caste.read_directive()
        assert "# Test Directive" in text
        assert "Dies ist ein Test." in text
    
    def test_read_directive_not_exists(self, workspace: Path):
        """read_directive() gibt Default zurück, wenn Datei fehlt."""
        caste = PlaceholderCaste(workspace_path=workspace)
        text = caste.read_directive()
        assert text == "(No directive set)"
    
    def test_read_theory_baseline_exists(self, workspace: Path, theory_file: Path):
        """read_theory_baseline() liest theory_baseline.md korrekt."""
        caste = PlaceholderCaste(workspace_path=workspace)
        text = caste.read_theory_baseline()
        assert "# Theory Baseline" in text
    
    def test_read_theory_baseline_not_exists(self, workspace: Path):
        """read_theory_baseline() gibt Default zurück, wenn Datei fehlt."""
        caste = PlaceholderCaste(workspace_path=workspace)
        text = caste.read_theory_baseline()
        assert text == "(No theory baseline yet)"
    
    def test_read_pheromones_filters_by_type(self, workspace: Path):
        """read_pheromones() filtert nach Typ."""
        caste = PlaceholderCaste(workspace_path=workspace)
        
        # Ein TRAIL-Pheromon schreiben (über das Feld der Kaste)
        from src.models.pheromone import Pheromone
        trail = Pheromone(
            id="trail_test",
            type=PheromoneType.TRAIL,
            strength=0.8,
            age_cycles=0,
            relevance=1.0,
            content="Test trail",
            tags=["test"],
            source_agent="test",
        )
        caste.pheromone_field.emit(trail)
        
        # Ein WARNING-Pheromon schreiben
        warning = Pheromone(
            id="warning_test",
            type=PheromoneType.WARNING,
            strength=0.5,
            age_cycles=0,
            relevance=1.0,
            content="Test warning",
            tags=["test"],
            source_agent="test",
        )
        caste.pheromone_field.emit(warning)
        
        # Nur TRAILs lesen (PlaceholderCaste darf nur TRAILs lesen)
        trails = caste.read_pheromones(pheromone_type=PheromoneType.TRAIL)
        assert len(trails) == 1
        assert trails[0].type == PheromoneType.TRAIL
    
    def test_read_pheromones_blocks_unauthorized_type(self, workspace: Path):
        """read_pheromones() blockiert unerlaubte Typen."""
        caste = PlaceholderCaste(workspace_path=workspace)
        
        # Ein WARNING-Pheromon schreiben (über das Feld der Kaste)
        from src.models.pheromone import Pheromone
        warning = Pheromone(
            id="warning_test",
            type=PheromoneType.WARNING,
            strength=0.5,
            age_cycles=0,
            relevance=1.0,
            content="Test warning",
            tags=["test"],
            source_agent="test",
        )
        caste.pheromone_field.emit(warning)
        
        # WARNING lesen versuchen (PlaceholderCaste darf nur TRAILs lesen)
        warnings = caste.read_pheromones(pheromone_type=PheromoneType.WARNING)
        assert warnings == []
    
    def test_write_pheromone_allowed(self, workspace: Path):
        """write_pheromone() schreibt Pheromon, wenn Typ erlaubt ist."""
        caste = PlaceholderCaste(workspace_path=workspace)
        
        pheromone = caste.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content="Test content",
            tags=["test"],
            strength=0.6,
            relevance=0.7,
        )
        
        assert pheromone.type == PheromoneType.TRAIL
        assert pheromone.content == "Test content"
        assert pheromone.strength == 0.6
        assert pheromone.relevance == 0.7
        assert pheromone.source_agent == CasteName.ANALYST.value
        
        # Überprüfen, dass es im Feld existiert
        field = PheromoneField(field_root=workspace / "01_Pheromon_Field")
        found = field.get(pheromone.id)
        assert found is not None
        assert found.content == "Test content"
    
    def test_write_pheromone_blocks_unauthorized(self, workspace: Path):
        """write_pheromone() wirft ValueError bei unerlaubtem Typ."""
        caste = PlaceholderCaste(workspace_path=workspace)
        
        with pytest.raises(ValueError) as exc_info:
            caste.write_pheromone(
                pheromone_type=PheromoneType.WARNING,
                content="Test content",
            )
        
        assert "not allowed to write" in str(exc_info.value)
        assert "warning" in str(exc_info.value).lower()
    
    def test_reinforce_pheromone(self, workspace: Path):
        """reinforce_pheromone() verstärkt ein Pheromon."""
        caste = PlaceholderCaste(workspace_path=workspace)
        field = PheromoneField(field_root=workspace / "01_Pheromon_Field")
        
        # Pheromon schreiben
        pheromone = caste.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content="Test",
            strength=0.5,
        )
        
        # Verstärken
        reinforced = caste.reinforce_pheromone(pheromone.id)
        assert reinforced is not None
        assert reinforced.strength > 0.5
    
    def test_weaken_pheromone(self, workspace: Path):
        """weaken_pheromone() schwächt ein Pheromon ab."""
        caste = PlaceholderCaste(workspace_path=workspace)
        field = PheromoneField(field_root=workspace / "01_Pheromon_Field")
        
        # Pheromon schreiben
        pheromone = caste.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content="Test",
            strength=0.5,
        )
        
        # Abschwächen
        weakened = caste.weaken_pheromone(pheromone.id)
        assert weakened is not None
        assert weakened.strength < 0.5
    
    def test_run_writes_shadow_memory_on_success(self, workspace: Path, tmp_path: Path):
        """run() schreibt Shadow Memory bei Erfolg."""
        caste = PlaceholderCaste(workspace_path=workspace)
        work_dir = tmp_path / "work_dir"
        work_dir.mkdir()
        
        result = caste.run(work_dir)
        
        assert result.success is True
        
        # Shadow Memory überprüfen
        shadow_dir = work_dir / "shadow_memory"
        assert shadow_dir.exists()
        shadow_file = shadow_dir / f"{caste.caste_name.value}_shadow.json"
        assert shadow_file.exists()
        
        data = json.loads(shadow_file.read_text(encoding="utf-8"))
        assert data["caste_name"] == caste.caste_name.value
        assert data["result"]["success"] is True
        assert "started_at" in data
        assert "finished_at" in data
        assert "duration_ms" in data
    
    def test_run_writes_shadow_memory_on_error(self, workspace: Path, tmp_path: Path):
        """run() schreibt Shadow Memory auch bei Fehler."""
        
        class FailingCaste(BaseCaste):
            caste_name = CasteName.HYPOTHESIZER
            role = "Tester"
            specialization = "Failing"
            reads_pheromones = []
            writes_pheromones = []
            
            def execute(self, work_dir: Path) -> CasteExecutionResult:
                raise RuntimeError("Test failure")
        
        caste = FailingCaste(workspace_path=workspace)
        work_dir = tmp_path / "work_dir"
        work_dir.mkdir()
        
        with pytest.raises(RuntimeError):
            caste.run(work_dir)
        
        # Shadow Memory sollte trotzdem geschrieben worden sein
        shadow_dir = work_dir / "shadow_memory"
        assert shadow_dir.exists()
        shadow_file = shadow_dir / f"{caste.caste_name.value}_shadow.json"
        assert shadow_file.exists()
        
        data = json.loads(shadow_file.read_text(encoding="utf-8"))
        assert data["result"]["success"] is False
        assert "Test failure" in data["result"]["error_message"]
    
    def test_run_throws_runtime_error_on_failure(self, workspace: Path, tmp_path: Path):
        """run() wirft RuntimeError bei Fehler in execute()."""
        
        class FailingCaste(BaseCaste):
            caste_name = CasteName.SIMULATOR
            role = "Tester"
            specialization = "Failing"
            reads_pheromones = []
            writes_pheromones = []
            
            def execute(self, work_dir: Path) -> CasteExecutionResult:
                raise ValueError("Test error")
        
        caste = FailingCaste(workspace_path=workspace)
        work_dir = tmp_path / "work_dir"
        work_dir.mkdir()
        
        with pytest.raises(RuntimeError) as exc_info:
            caste.run(work_dir)
        
        assert "failed" in str(exc_info.value).lower()
    
    def test_shadow_memory_in_workspace_root_if_no_work_dir(self, workspace: Path):
        """Shadow Memory wird im Workspace-Root geschrieben, wenn kein work_dir."""
        caste = PlaceholderCaste(workspace_path=workspace)
        
        result = caste.run(None)  # Kein work_dir
        
        # Shadow Memory sollte im Workspace-Root sein
        shadow_dir = workspace / "00_System" / "shadow_memory"
        assert shadow_dir.exists()
        shadow_file = shadow_dir / f"{caste.caste_name.value}_shadow.json"
        assert shadow_file.exists()


class TestPlaceholderCaste:
    """Tests für die PlaceholderCaste."""
    
    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        """Erstellt einen temporären Workspace."""
        ws = tmp_path / "test_workspace"
        ws.mkdir()
        (ws / "00_System").mkdir()
        (ws / "01_Pheromon_Field").mkdir()
        (ws / "01_Pheromon_Field" / "trails").mkdir()
        (ws / "01_Pheromon_Field" / "crystals").mkdir()
        (ws / "01_Pheromon_Field" / "warnings").mkdir()
        return ws
    
    def test_placeholder_is_valid_subclass(self, workspace: Path):
        """PlaceholderCaste ist eine gültige BaseCaste-Subklasse."""
        caste = PlaceholderCaste(workspace_path=workspace)
        assert isinstance(caste, BaseCaste)
        assert caste.caste_name == CasteName.ANALYST
    
    def test_placeholder_execute_reads_and_writes(self, workspace: Path, tmp_path: Path):
        """PlaceholderCaste.execute() liest und schreibt Pheromone."""
        caste = PlaceholderCaste(workspace_path=workspace)
        
        # Ein Trail schreiben, der gelesen werden kann (über das Feld der Kaste)
        from src.models.pheromone import Pheromone
        caste.pheromone_field.emit(Pheromone(
            id="trail_1",
            type=PheromoneType.TRAIL,
            strength=0.7,
            age_cycles=0,
            relevance=1.0,
            content="Existing trail",
            tags=["test"],
            source_agent="test",
        ))
        
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        
        result = caste.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_read == 1
        assert result.pheromones_written == 1
        assert "new_pheromone_id" in result.extra_data
        assert "trails_read_ids" in result.extra_data
    
    def test_caste_execution_result_has_correct_stats(self, workspace: Path, tmp_path: Path):
        """CasteExecutionResult hat korrekte Statistiken."""
        caste = PlaceholderCaste(workspace_path=workspace)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        
        result = caste.run(work_dir)
        
        assert isinstance(result, CasteExecutionResult)
        assert result.caste_name == CasteName.ANALYST
        assert result.success is True
        assert result.pheromones_read >= 0
        assert result.pheromones_written >= 0
        assert isinstance(result.output_files, list)
        assert result.error_message is None

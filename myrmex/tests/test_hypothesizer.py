"""Tests für die HypothesizerCaste."""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.castes.hypothesizer import HypothesizerCaste
from src.models.caste import CasteName
from src.models.pheromone import Pheromone, PheromoneType
from src.pheromones.pheromone_field import PheromoneField


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace für Tests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # Benötigte Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "04_Knowledge_Base").mkdir(parents=True)
    
    yield workspace_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def hypothesizer(temp_workspace):
    """Erstellt eine HypothesizerCaste mit temporärem Workspace."""
    return HypothesizerCaste(workspace_path=temp_workspace)


@pytest.fixture
def analysis_pheromones(temp_workspace, hypothesizer):
    """Erstellt TRAIL-Pheromone mit Analyse-Tags."""
    # Verwende das gleiche PheromoneField wie die HypothesizerCaste
    field = hypothesizer.pheromone_field
    
    pheromones = []
    for i, (content, tags, source) in enumerate([
        ("Fluorescence decreases faster than simulated", ["analysis", "discrepancy"], "analyst"),
        ("Temperature plateau reached at 35.8°C", ["analysis"], "analyst"),
        ("Simulated pH drop matches theory", ["simulation"], "simulator"),
        ("Unrelated trail without analysis tag", ["other"], "executor"),
    ]):
        pheromone = Pheromone(
            id=f"analysis_pheromone_{i}",
            type=PheromoneType.TRAIL,
            content=content,
            tags=tags,
            source_agent=source,
            strength=0.5,
            relevance=0.5,
            age_cycles=0,
        )
        field.emit(pheromone)
        pheromones.append(pheromone)
    
    return pheromones


@pytest.fixture
def valid_theory_baseline():
    """Eine gültige theory_baseline.md."""
    return "# Theory Baseline\n\nSome plausible scientific content here.\n"


class TestHypothesizerCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_hypothesizer(self):
        """caste_name ist HYPOTHESIZER."""
        assert HypothesizerCaste.caste_name == CasteName.HYPOTHESIZER
    
    def test_reads_trail_and_writes_trail(self):
        """reads TRAIL, writes TRAIL."""
        assert PheromoneType.TRAIL in HypothesizerCaste.reads_pheromones
        assert PheromoneType.TRAIL in HypothesizerCaste.writes_pheromones


class TestHypothesizerGeneration:
    """Tests für die Hypothesen-Generierung."""
    
    def test_no_analysis_pheromones_returns_early(self, hypothesizer, temp_workspace):
        """Ohne Analyse-Pheromone wird früh zurückgekehrt."""
        # Keine Pheromone im Feld
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.pheromones_read == 0
        assert result.pheromones_written == 0
        assert result.extra_data.get("reason") == "no_analysis_pheromones"
    
    def test_generates_hypothesis_from_analysis_pheromones(self, hypothesizer, temp_workspace, analysis_pheromones):
        """Hypothese wird aus Analyse-Pheromonen generiert."""
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.pheromones_read > 0  # Mindestens eines gelesen
        assert result.pheromones_written == 1
        assert result.extra_data.get("hypothesis_count") == 1
        assert result.extra_data.get("analysis_pheromones_used") > 0
    
    def test_writes_hypothesis_file(self, hypothesizer, temp_workspace, analysis_pheromones):
        """hypothesis.md wird geschrieben."""
        work_dir = temp_workspace / "00_System"
        result = hypothesizer.execute(work_dir)
        
        hypothesis_path = work_dir / "hypothesis.md"
        assert hypothesis_path.exists()
        assert result.output_files == ["hypothesis.md"]
        assert result.extra_data.get("hypothesis_path") == str(hypothesis_path)
    
    def test_writes_hypothesis_pheromone(self, hypothesizer, temp_workspace, analysis_pheromones):
        """TRAIL-Pheromon mit Tag 'hypothesis' wird geschrieben."""
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        assert result.pheromones_written == 1
        
        # Das Pheromon sollte im Feld sein
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        hypothesis_pheromones = [
            p for p in all_pheromones 
            if p.type == PheromoneType.TRAIL and "hypothesis" in p.tags
        ]
        assert len(hypothesis_pheromones) >= 1
    
    def test_hypothesis_uses_theory_context(self, hypothesizer, temp_workspace, analysis_pheromones, valid_theory_baseline):
        """theory_baseline.md wird gelesen (auch wenn sie leer ist)."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(valid_theory_baseline, encoding="utf-8")
        
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        assert result.success is True
        # Die Hypothese sollte generiert werden
        assert result.pheromones_written == 1
    
    def test_multiple_findings_produce_richer_hypothesis(self, hypothesizer, temp_workspace):
        """Mehrere Analyse-Pheromone erzeugen eine reichhaltigere Hypothese."""
        # Verwende das gleiche PheromoneField wie die HypothesizerCaste
        field = hypothesizer.pheromone_field
        
        # Erstelle 3 Analyse-Pheromone
        for i in range(3):
            pheromone = Pheromone(
                id=f"multi_analysis_{i}",
                type=PheromoneType.TRAIL,
                content=f"Finding number {i}: some important data point",
                tags=["analysis"],
                source_agent="analyst",
                strength=0.5,
                relevance=0.5,
                age_cycles=0,
            )
            field.emit(pheromone)
        
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("analysis_pheromones_used") == 3
        
        # Überprüfe den Inhalt der hypothesis.md
        hypothesis_path = temp_workspace / "00_System" / "hypothesis.md"
        content = hypothesis_path.read_text(encoding="utf-8")
        
        # Bei mehreren Findings sollte die Hypothese auf "systematic relationship" hinweisen
        assert "systematic relationship" in content or "Based on 3 analysis findings" in content


class TestHypothesizerPheromones:
    """Tests für die Pheromon-Ausgabe."""
    
    def test_hypothesis_pheromone_has_correct_tags(self, hypothesizer, temp_workspace, analysis_pheromones):
        """Das Hypothesen-Pheromon hat die korrekten Tags."""
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        
        # Finde das zuletzt geschriebene Pheromon
        hypothesis_pheromones = [
            p for p in all_pheromones 
            if p.type == PheromoneType.TRAIL and "hypothesis" in p.tags
        ]
        
        assert len(hypothesis_pheromones) >= 1
        pheromone = hypothesis_pheromones[-1]  # Das zuletzt geschriebene
        
        assert "hypothesis" in pheromone.tags
        assert "experiment_iteration" in pheromone.tags
        assert pheromone.strength == 0.6
        assert pheromone.relevance == 0.8
    
    def test_hypothesis_pheromone_content_summary(self, hypothesizer, temp_workspace, analysis_pheromones):
        """Das Hypothesen-Pheromon enthält eine Zusammenfassung."""
        result = hypothesizer.execute(temp_workspace / "00_System")
        
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        
        hypothesis_pheromones = [
            p for p in all_pheromones 
            if p.type == PheromoneType.TRAIL and "hypothesis" in p.tags
        ]
        
        assert len(hypothesis_pheromones) >= 1
        pheromone = hypothesis_pheromones[-1]
        
        # Der Content sollte eine Zusammenfassung enthalten
        assert "Hypothesis:" in pheromone.content or "Proposed:" in pheromone.content

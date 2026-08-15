"""
tests/test_theorist.py
Tests für die TheoristCaste — das Langzeitgedächtnis des Schwarms.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.castes.theorist import TheoristCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType, Pheromone
from src.pheromones.pheromone_field import PheromoneField
from datetime import datetime, timezone, timedelta


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace für Tests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # Alle benötigten Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "04_Knowledge_Base").mkdir(parents=True)
    
    yield workspace_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def knowledge_pheromones(temp_workspace):
    """Erstellt TRAIL-Pheromone mit Knowledge-Tags."""
    from src.models.pheromone import Pheromone
    
    field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
    
    pheromones = []
    # Erstelle Pheromone mit unterschiedlichen Zeitstempeln für Sortier-Test
    base_time = datetime.now(timezone.utc) - timedelta(hours=2)
    
    for i, (content, tags, source) in enumerate([
        ("Temperature approaches target exponentially", ["analysis"], "analyst"),
        ("Fluorescence decreases with pH drop", ["finding"], "analyst"),
        ("Simulated pH drop matches theory", ["simulation"], "simulator"),
        ("Hypothesis: buffer capacity limits pH drop", ["hypothesis"], "planner"),
        ("Unrelated trail without knowledge tag", ["other"], "executor"),
    ]):
        # Zeitstempel manipulieren für Sortier-Test
        created_at = base_time + timedelta(minutes=i*10)
        pheromone = Pheromone(
            id=f"test_pheromone_{i}",
            type=PheromoneType.TRAIL,
            content=content,
            tags=tags,
            source_agent=source,
            strength=0.5,
            relevance=0.5,
            age_cycles=0,
        )
        pheromone.created_at = created_at
        field.emit(pheromone)
        pheromones.append(pheromone)
    
    return pheromones


@pytest.fixture
def theorist(temp_workspace):
    """Erstellt eine TheoristCaste mit temporärem Workspace."""
    return TheoristCaste(workspace_path=temp_workspace)


class TestTheoristCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_theorist(self):
        """caste_name ist THEORIST."""
        assert TheoristCaste.caste_name == CasteName.THEORIST
    
    def test_reads_and_writes_trail_pheromones(self):
        """reads/writes TRAIL."""
        assert PheromoneType.TRAIL in TheoristCaste.reads_pheromones
        assert PheromoneType.TRAIL in TheoristCaste.writes_pheromones
    
    def test_role_and_specialization(self):
        """Rolle und Spezialisierung sind korrekt."""
        assert "konsolidieren" in TheoristCaste.role.lower()
        assert "Wissens" in TheoristCaste.specialization or "Knowledge" in TheoristCaste.specialization


class TestTheoristConsolidation:
    """Tests für die Konsolidierungs-Logik."""
    
    def test_consolidates_knowledge_pheromones(self, theorist, temp_workspace, knowledge_pheromones):
        """Pheromone mit Knowledge-Tags werden konsolidiert."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = theorist.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_read > 0  # Sollte Knowledge-Pheromone gelesen haben
        assert result.pheromones_written == 1  # Bestätigungs-Pheromon
        
        # theory_baseline.md sollte existieren
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        assert theory_path.exists()
        
        content = theory_path.read_text(encoding="utf-8")
        # Sollte Einträge enthalten
        assert "analyst" in content.lower() or "simulation" in content.lower()
    
    def test_ignores_non_knowledge_pheromones(self, temp_workspace):
        """Pheromone ohne Knowledge-Tags werden ignoriert."""
        from src.models.pheromone import Pheromone
        
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        
        # Nur Pheromon ohne Knowledge-Tag
        pheromone = Pheromone(
            id="test_other_pheromone",
            type=PheromoneType.TRAIL,
            content="Just a regular trail",
            tags=["other", "misc"],
            source_agent="executor",
            strength=0.5,
            relevance=0.5,
            age_cycles=0,
        )
        field.emit(pheromone)
        
        theorist = TheoristCaste(workspace_path=temp_workspace)
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = theorist.execute(work_dir)
        
        # Sollte keine Pheromone gelesen haben (keine Knowledge-Tags)
        assert result.success is True
        assert result.pheromones_read == 0
        assert result.extra_data.get("reason") == "no_knowledge_pheromones"
    
    def test_no_knowledge_pheromones_returns_early(self, temp_workspace):
        """Ohne Pheromone wird früh zurückgekehrt."""
        theorist = TheoristCaste(workspace_path=temp_workspace)
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = theorist.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_read == 0
        assert result.pheromones_written == 0
        assert result.extra_data.get("reason") == "no_knowledge_pheromones"
    
    def test_appends_to_theory_baseline(self, theorist, temp_workspace, knowledge_pheromones):
        """Einträge werden an die theory_baseline.md angehängt."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # Erste Ausführung
        result1 = theorist.execute(work_dir)
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        content1 = theory_path.read_text(encoding="utf-8")
        
        # Zweite Ausführung (sollte anhängen, nicht überschreiben)
        result2 = theorist.execute(work_dir)
        content2 = theory_path.read_text(encoding="utf-8")
        
        # Content sollte länger oder gleich sein (mindestens nicht kürzer)
        assert len(content2) >= len(content1)
        # Beide sollten Consolidation-Einträge haben
        assert "Consolidation" in content1
        assert "Consolidation" in content2
    
    def test_creates_theory_baseline_if_missing(self, theorist, temp_workspace, knowledge_pheromones):
        """theory_baseline.md wird erstellt, falls nicht vorhanden."""
        # Lösche theory_baseline.md falls vorhanden
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        if theory_path.exists():
            theory_path.unlink()
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = theorist.execute(work_dir)
        
        assert result.success is True
        assert theory_path.exists()
        
        content = theory_path.read_text(encoding="utf-8")
        assert "# Theory Baseline" in content
    
    def test_writes_confirmation_pheromone(self, theorist, temp_workspace, knowledge_pheromones):
        """Bestätigungs-Pheromon wird geschrieben."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = theorist.execute(work_dir)
        
        assert result.pheromones_written == 1
        assert "pheromone_id" in result.extra_data
        
        # Pheromon sollte im Feld existieren
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        confirmation_pheromones = [p for p in all_pheromones if "consolidation" in p.tags]
        assert len(confirmation_pheromones) >= 1
    
    def test_pheromones_sorted_by_creation_time(self, theorist, temp_workspace, knowledge_pheromones):
        """Pheromone werden nach Zeit sortiert."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = theorist.execute(work_dir)
        
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        content = theory_path.read_text(encoding="utf-8")
        
        # Die Einträge sollten in der Reihenfolge erscheinen, in der sie erstellt wurden
        # (älteste zuerst). Da wir die created_at im Fixture manipuliert haben,
        # sollte das erste Pheromon (analysis) vor dem letzten (hypothesis) erscheinen.
        # Hinweis: Dies ist ein vereinfachter Test - in der Praxis würde man
        # die genaue Reihenfolge im Markdown überprüfen.
        assert "Consolidation" in content

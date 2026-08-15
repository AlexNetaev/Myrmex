"""
tests/test_archivist.py
Tests für die ArchivistCaste — Token-Hygiene und Archivierung des Langzeitgedächtnisses.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.castes.archivist import ArchivistCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType, Pheromone
from src.pheromones.pheromone_field import PheromoneField
from datetime import datetime, timezone


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
def archivist(temp_workspace):
    """Erstellt eine ArchivistCaste mit temporärem Workspace."""
    return ArchivistCaste(workspace_path=temp_workspace)


@pytest.fixture
def long_theory_baseline():
    """Eine theory_baseline.md mit mehreren Consolidation-Blöcken, die zusammen zu lang ist."""
    blocks = []
    for i in range(6):
        block = f"\n## Consolidation (2026-08-{i+10}T10:00:00+00:00)\n"
        block += f"- **[analyst]** (analysis): Finding number {i} " + "x" * 1500 + "\n"
        blocks.append(block)
    header = "# Theory Baseline\n\n*(Consolidated knowledge from the swarm.)*\n"
    return header + "\n".join(blocks)


@pytest.fixture
def short_theory_baseline():
    """Eine kurze theory_baseline.md unter MAX_BASELINE_CHARS."""
    header = "# Theory Baseline\n\n*(Consolidated knowledge from the swarm.)*\n"
    block = "\n## Consolidation (2026-08-10T10:00:00+00:00)\n"
    block += "- **[analyst]** (analysis): Short finding\n"
    return header + block


class TestArchivistCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_archivist(self):
        """caste_name ist ARCHIVIST."""
        assert ArchivistCaste.caste_name == CasteName.ARCHIVIST
    
    def test_reads_trail_and_writes_trail(self):
        """reads TRAIL, writes TRAIL."""
        assert PheromoneType.TRAIL in ArchivistCaste.reads_pheromones
        assert PheromoneType.TRAIL in ArchivistCaste.writes_pheromones
    
    def test_role_and_specialization(self):
        """Rolle und Spezialisierung sind korrekt."""
        assert "Token-Hygiene" in ArchivistCaste.role or "schlank" in ArchivistCaste.role.lower()
        assert "Archivierung" in ArchivistCaste.specialization or "Kompression" in ArchivistCaste.specialization


class TestArchivistTokenHygiene:
    """Tests für die Token-Hygiene-Logik."""
    
    def test_no_theory_baseline_returns_early(self, archivist, temp_workspace):
        """Ohne Baseline wird früh zurückgekehrt."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_read == 0
        assert result.pheromones_written == 0
        assert result.extra_data.get("reason") == "no_theory_baseline"
    
    def test_baseline_within_budget_no_compression(self, archivist, temp_workspace, short_theory_baseline):
        """Baseline unter MAX_BASELINE_CHARS wird nicht komprimiert."""
        # Kurze Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(short_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        assert result.extra_data.get("reason") == "no_compression_needed"
        assert len(short_theory_baseline) <= ArchivistCaste.MAX_BASELINE_CHARS
    
    def test_not_enough_blocks_no_archive(self, archivist, temp_workspace):
        """Zu wenige Blöcke → nichts wird archiviert."""
        # Baseline mit nur 2 Blöcken erstellen (weniger als KEEP_RECENT_BLOCKS=3)
        header = "# Theory Baseline\n\n*(Consolidated knowledge from the swarm.)*\n"
        blocks = []
        for i in range(2):
            block = f"\n## Consolidation (2026-08-{i+10}T10:00:00+00:00)\n"
            block += "- **[analyst]** (analysis): " + "x" * 4000 + "\n"
            blocks.append(block)
        content = header + "\n".join(blocks)
        
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(content, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        assert result.extra_data.get("reason") == "not_enough_blocks_to_archive"
    
    def test_archives_oldest_blocks_when_too_long(self, archivist, temp_workspace, long_theory_baseline):
        """Älteste Blöcke werden ins Archiv verschoben."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_written == 1
        
        # Archive sollte existieren
        archive_path = temp_workspace / "04_Knowledge_Base" / "Archive" / "theory_archive.md"
        assert archive_path.exists()
        
        # Archiv sollte die ältesten Blöcke enthalten
        archive_content = archive_path.read_text(encoding="utf-8")
        assert "2026-08-10" in archive_content  # Ältester Block
        assert "2026-08-11" in archive_content  # Zweitältester Block
    
    def test_keeps_recent_blocks(self, archivist, temp_workspace, long_theory_baseline):
        """Die neuesten Blöcke bleiben in der aktiven Baseline."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        
        # Baseline sollte nur noch die neuesten Blöcke enthalten
        new_content = theory_path.read_text(encoding="utf-8")
        
        # Die neuesten Blöcke (2026-08-13, 14, 15) sollten enthalten sein
        assert "2026-08-13" in new_content
        assert "2026-08-14" in new_content
        assert "2026-08-15" in new_content
        
        # Die ältesten Blöcke (2026-08-10, 11, 12) sollten NICHT in der Baseline sein
        assert "2026-08-10" not in new_content
        assert "2026-08-11" not in new_content
        assert "2026-08-12" not in new_content
    
    def test_baseline_length_reduced(self, archivist, temp_workspace, long_theory_baseline):
        """Die Baseline ist nach der Archivierung kürzer."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        original_length = len(long_theory_baseline)
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        
        # Neue Länge sollte kleiner sein
        new_content = theory_path.read_text(encoding="utf-8")
        new_length = len(new_content)
        
        assert new_length < original_length
        assert result.extra_data.get("baseline_length_before") == original_length
        assert result.extra_data.get("baseline_length_after") == new_length
    
    def test_header_preserved_after_archiving(self, archivist, temp_workspace, long_theory_baseline):
        """Der Header bleibt nach der Archivierung erhalten."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        
        # Header sollte erhalten bleiben
        new_content = theory_path.read_text(encoding="utf-8")
        assert "# Theory Baseline" in new_content
        assert "Consolidated knowledge from the swarm" in new_content


class TestArchivistPheromones:
    """Tests für die Pheromon-Ausgabe."""
    
    def test_writes_confirmation_pheromone(self, archivist, temp_workspace, long_theory_baseline):
        """Bestätigungs-Pheromon wird geschrieben."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_written == 1
        assert "pheromone_id" in result.extra_data
    
    def test_pheromone_has_correct_tags(self, archivist, temp_workspace, long_theory_baseline):
        """Das Pheromon hat die Tags ["archive", "token_hygiene"]."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        
        # Pheromon im Feld überprüfen
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        
        # Das geschriebene Pheromon finden
        pheromone_id = result.extra_data.get("pheromone_id")
        confirmation_pheromone = None
        for p in all_pheromones:
            if p.id == pheromone_id:
                confirmation_pheromone = p
                break
        
        assert confirmation_pheromone is not None
        assert "archive" in confirmation_pheromone.tags
        assert "token_hygiene" in confirmation_pheromone.tags
    
    def test_pheromone_content_summary(self, archivist, temp_workspace, long_theory_baseline):
        """Das Pheromon enthält eine Zusammenfassung der Archivierung."""
        # Lange Baseline schreiben
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(long_theory_baseline, encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = archivist.execute(work_dir)
        
        assert result.success is True
        
        # Pheromon im Feld überprüfen
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        
        # Das geschriebene Pheromon finden
        pheromone_id = result.extra_data.get("pheromone_id")
        confirmation_pheromone = None
        for p in all_pheromones:
            if p.id == pheromone_id:
                confirmation_pheromone = p
                break
        
        assert confirmation_pheromone is not None
        assert "Archivist" in confirmation_pheromone.content or "archived" in confirmation_pheromone.content.lower()
        assert "block" in confirmation_pheromone.content.lower()

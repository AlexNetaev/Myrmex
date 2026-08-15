"""Tests für die GuardianCaste."""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.castes.guardian import GuardianCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType
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
def guardian(temp_workspace):
    """Erstellt eine GuardianCaste mit temporärem Workspace."""
    return GuardianCaste(workspace_path=temp_workspace)


@pytest.fixture
def valid_theory_baseline():
    """Eine gültige theory_baseline.md."""
    return "# Theory Baseline\n\nSome plausible scientific content here.\n"


@pytest.fixture
def implausible_theory_baseline():
    """Eine theory_baseline.md mit unplausiblen Werten."""
    return (
        "# Theory Baseline\n\n"
        "The reaction reaches -300 °C which is impossible.\n"
        "The efficiency is 150% which violates thermodynamics.\n"
    )


class TestGuardianCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_guardian(self):
        """caste_name ist GUARDIAN."""
        assert GuardianCaste.caste_name == CasteName.GUARDIAN
    
    def test_reads_trail_and_writes_trail_and_warning(self):
        """reads TRAIL, writes TRAIL und WARNING."""
        assert PheromoneType.TRAIL in GuardianCaste.reads_pheromones
        assert PheromoneType.TRAIL in GuardianCaste.writes_pheromones
        assert PheromoneType.WARNING in GuardianCaste.writes_pheromones


class TestGuardianValidation:
    """Tests für die Validierungslogik."""
    
    def test_missing_file_reports_violation(self, guardian, temp_workspace):
        """Fehlende Datei wird gemeldet."""
        # theory_baseline.md existiert nicht
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        if theory_path.exists():
            theory_path.unlink()
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        assert len(result.extra_data.get("violations", [])) > 0
    
    def test_empty_file_reports_violation(self, guardian, temp_workspace):
        """Leere Datei wird gemeldet."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text("", encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        violations = result.extra_data.get("violations", [])
        assert any("empty" in v.lower() for v in violations)
    
    def test_valid_file_passes(self, guardian, temp_workspace, valid_theory_baseline):
        """Gültige Datei besteht alle Checks."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(valid_theory_baseline, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is True
        assert result.extra_data.get("violations", []) == []
    
    def test_file_without_header_reports_violation(self, guardian, temp_workspace):
        """Datei ohne Header wird gemeldet."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text("Just plain text without any headers.\n", encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        violations = result.extra_data.get("violations", [])
        assert any("header" in v.lower() for v in violations)
    
    def test_file_too_long_reports_violation(self, guardian, temp_workspace):
        """Zu lange Datei wird gemeldet."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        # Erstelle Inhalt > 8000 Zeichen
        content = "# Theory Baseline\n\n" + "A" * 9000
        theory_path.write_text(content, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        violations = result.extra_data.get("violations", [])
        assert any("characters" in v.lower() or "exceeding" in v.lower() for v in violations)
    
    def test_implausible_temperature_reports_violation(self, guardian, temp_workspace, implausible_theory_baseline):
        """Unplausible Temperatur wird gemeldet."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(implausible_theory_baseline, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        violations = result.extra_data.get("violations", [])
        assert any("temperature" in v.lower() or "-300" in v for v in violations)
    
    def test_efficiency_above_100_reports_violation(self, guardian, temp_workspace, implausible_theory_baseline):
        """Effizienz über 100% wird gemeldet."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(implausible_theory_baseline, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        violations = result.extra_data.get("violations", [])
        assert any("efficiency" in v.lower() or "150%" in v or "100%" in v for v in violations)
    
    def test_negative_concentration_reports_violation(self, guardian, temp_workspace):
        """Negative Konzentration wird gemeldet."""
        content = "# Theory Baseline\n\nThe concentration is -5.0 mM which is impossible.\n"
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(content, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False
        violations = result.extra_data.get("violations", [])
        assert any("negative" in v.lower() or "concentration" in v.lower() for v in violations)


class TestGuardianPheromones:
    """Tests für die Pheromon-Ausgabe."""
    
    def test_writes_trail_pheromone_on_success(self, guardian, temp_workspace, valid_theory_baseline):
        """TRAIL-Pheromon bei Erfolg."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(valid_theory_baseline, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.pheromones_written == 1
        # Das Pheromon sollte im Feld sein
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        trail_pheromones = [p for p in all_pheromones if p.type == PheromoneType.TRAIL]
        assert len(trail_pheromones) >= 1
    
    def test_writes_warning_pheromone_on_violation(self, guardian, temp_workspace):
        """WARNING-Pheromon bei Verletzung."""
        # Leere Datei erzeugt Verletzung
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text("", encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.pheromones_written == 1
        # Das Pheromon sollte ein WARNING sein
        field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")
        all_pheromones = field.scan()
        warning_pheromones = [p for p in all_pheromones if p.type == PheromoneType.WARNING]
        assert len(warning_pheromones) >= 1


class TestGuardianDirectoryHandling:
    """Tests für die Verzeichnis-Behandlung."""
    
    def test_handles_existing_knowledge_base_directory(self, guardian, temp_workspace, valid_theory_baseline):
        """Verzeichnis existiert bereits."""
        theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
        theory_path.write_text(valid_theory_baseline, encoding="utf-8")
        
        result = guardian.execute(temp_workspace / "00_System")
        
        assert result.success is True
    
    def test_handles_missing_knowledge_base_directory(self, temp_workspace):
        """Verzeichnis existiert nicht."""
        # Lösche das Knowledge-Base-Verzeichnis
        kb_dir = temp_workspace / "04_Knowledge_Base"
        if kb_dir.exists():
            import shutil
            shutil.rmtree(kb_dir)
        
        guardian = GuardianCaste(workspace_path=temp_workspace)
        result = guardian.execute(temp_workspace / "00_System")
        
        # Sollte erfolgreich sein, aber mit Violation (Datei existiert nicht)
        assert result.success is True
        assert result.extra_data.get("validation_passed") is False

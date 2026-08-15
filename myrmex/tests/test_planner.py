"""Tests für die PlannerCaste."""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml

from src.castes.planner import PlannerCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType
from src.castes.ofat import OFAT_PARAMETER_SEQUENCE


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace für Tests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    system_dir = workspace_path / "00_System"
    system_dir.mkdir(parents=True)
    pheromon_dir = workspace_path / "01_Pheromon_Field"
    pheromon_dir.mkdir(parents=True)
    yield workspace_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def planner(temp_workspace):
    """Erstellt eine PlannerCaste mit temporärem Workspace."""
    return PlannerCaste(workspace_path=temp_workspace)


class TestPlannerCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_planner(self):
        assert PlannerCaste.caste_name == CasteName.PLANNER
    
    def test_reads_trail_pheromones(self):
        assert PheromoneType.TRAIL in PlannerCaste.reads_pheromones
    
    def test_writes_trail_pheromones(self):
        assert PheromoneType.TRAIL in PlannerCaste.writes_pheromones


class TestPlannerExecution:
    """Tests für die Ausführung der PlannerCaste."""
    
    def test_creates_baseline_profile_when_none_exists(self, planner, temp_workspace):
        """Wenn kein Profil existiert, wird ein Basis-Profil erstellt."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = planner.execute(work_dir)
        
        assert result.success is True
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        assert profile_path.exists()
        
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        assert profile["experiment_type"] == "fenton_fluorescence"
        for config in OFAT_PARAMETER_SEQUENCE:
            assert config.name in profile["parameters"]
    
    def test_applies_ofat_step_when_profile_exists(self, planner, temp_workspace):
        """Wenn ein Profil existiert, wird der nächste OFAT-Schritt angewendet."""
        # Erstelle ein Profil mit einem bekannten Wert
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        initial_profile = {
            "experiment_type": "fenton_fluorescence",
            "parameters": {"ascorbic_acid_concentration_mm": 25.0},
            "ofat_state": {
                "current_parameter_index": 0,
                "parameter_sequence": [config.name for config in OFAT_PARAMETER_SEQUENCE],
                "iterations_completed": 0,
            },
        }
        profile_path.write_text(yaml.dump(initial_profile), encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = planner.execute(work_dir)
        
        assert result.success is True
        
        new_profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        first_param_config = OFAT_PARAMETER_SEQUENCE[0]
        expected_value = 25.0 + first_param_config.step
        assert new_profile["parameters"]["ascorbic_acid_concentration_mm"] == expected_value
    
    def test_writes_trail_pheromone(self, planner, temp_workspace):
        """Die PlannerCaste schreibt ein TRAIL-Pheromon."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = planner.execute(work_dir)
        
        assert result.pheromones_written == 1
        assert "pheromone_id" in result.extra_data
    
    def test_result_contains_plan_description(self, planner, temp_workspace):
        """Das Ergebnis enthält eine Plan-Beschreibung."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = planner.execute(work_dir)
        
        assert "plan_description" in result.extra_data
        assert len(result.extra_data["plan_description"]) > 0
    
    def test_handles_malformed_profile_gracefully(self, planner, temp_workspace):
        """Ein ungültiges Profil wird gracefully behandelt."""
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("not: valid: yaml: {{{{", encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = planner.execute(work_dir)
        
        # Sollte trotzdem erfolgreich sein (erstellt ein Basis-Profil)
        assert result.success is True
    
    def test_profile_written_atomically(self, planner, temp_workspace):
        """Das Profil wird atomar geschrieben (keine .tmp-Datei nach Abschluss)."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        planner.execute(work_dir)
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        temp_path = profile_path.with_suffix(".yaml.tmp")
        assert not temp_path.exists()

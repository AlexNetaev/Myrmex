"""Tests für die ExecutorCaste und das Hardware-Profil."""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml
import json

from src.castes.executor import ExecutorCaste, HardwareValidationException
from src.castes.hardware_profile import (
    load_hardware_profile,
    find_active_profile,
    HardwareProfile,
)
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace für Tests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "03_Hardware_Queue").mkdir(parents=True)
    (workspace_path / "hardware_profiles").mkdir(parents=True)
    
    yield workspace_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def hardware_profile_path(temp_workspace):
    """Kopiert das orbus_dummy_v2.yaml in den temporären Workspace."""
    src = Path(__file__).parent.parent / "hardware_profiles" / "orbus_dummy_v2.yaml"
    if src.exists():
        dst = temp_workspace / "hardware_profiles" / "orbus_dummy_v2.yaml"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return dst
    return None


@pytest.fixture
def valid_experiment_profile():
    """Ein gültiges experiment_profile.yaml für Tests."""
    return {
        "experiment_type": "fenton_fluorescence",
        "cycle_id": "Cycle_001",
        "parameters": {
            "ascorbic_acid_concentration_mm": 25.0,
            "fecl3_concentration_mm": 1.0,
            "h2o2_concentration_mm": 50.0,
            "fluorescein_concentration_mm": 0.01,
            "phosphate_buffer_concentration_mm": 50.0,
            "target_temperature_c": 37.0,
            "mixing_speed_rpm": 600,
            "mixing_time_s": 15.0,
            "heating_time_s": 30.0,
            "measurement_interval_ms": 500,
            "fluorescence_duration_s": 60.0,
            "reagents": [
                {"reagent_name": "ascorbic_acid", "volume_ul": 500.0, "concentration_mm": 25.0},
                {"reagent_name": "fecl3", "volume_ul": 100.0, "concentration_mm": 1.0},
                {"reagent_name": "h2o2", "volume_ul": 200.0, "concentration_mm": 50.0},
                {"reagent_name": "fluorescein", "volume_ul": 100.0, "concentration_mm": 0.01},
                {"reagent_name": "phosphate_buffer", "volume_ul": 100.0, "concentration_mm": 50.0},
            ],
        },
    }


class TestHardwareProfileLoader:
    """Tests für den Hardware-Profil-Loader."""
    
    def test_load_valid_profile(self, hardware_profile_path):
        """Lädt das orbus_dummy_v2.yaml erfolgreich."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        profile = load_hardware_profile(hardware_profile_path)
        assert isinstance(profile, HardwareProfile)
        assert profile.metadata["name"] == "OrbusSim Dummy V2"
        assert profile.metadata["version"] == "2.0.0"
        assert "target_temperature_c" in profile.limits
    
    def test_load_nonexistent_profile(self):
        """Wirft FileNotFoundError bei nicht existierendem Profil."""
        with pytest.raises(FileNotFoundError):
            load_hardware_profile(Path("/nonexistent/path.yaml"))
    
    def test_find_active_profile(self, temp_workspace, hardware_profile_path):
        """Findet das erste Profil im Verzeichnis."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        profiles_dir = temp_workspace / "hardware_profiles"
        found_path = find_active_profile(profiles_dir)
        assert found_path is not None
        assert found_path.name == "orbus_dummy_v2.yaml"


class TestExecutorCaste:
    """Tests für die ExecutorCaste."""
    
    def test_executor_caste_definition(self):
        """caste_name ist EXECUTOR."""
        assert ExecutorCaste.caste_name == CasteName.EXECUTOR
        assert PheromoneType.TRAIL in ExecutorCaste.reads_pheromones
        assert PheromoneType.TRAIL in ExecutorCaste.writes_pheromones
    
    def test_validate_valid_profile(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Ein gültiges Profil wird akzeptiert."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        # Profil speichern
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        # Executor erstellen
        executor = ExecutorCaste(workspace_path=temp_workspace)
        result = executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        assert result.success is True
        assert result.pheromones_written == 1
    
    def test_validate_temperature_exceeds_limit(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Temperatur über Limit wird erkannt."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        # Temperatur über Maximum setzen (75.0 ist Max)
        valid_experiment_profile["parameters"]["target_temperature_c"] = 80.0
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        result = executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        assert result.success is False
        assert "target_temperature_c" in result.error_message
        assert "Maximum" in result.error_message
    
    def test_validate_missing_reagent(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Fehlendes Reagenz wird erkannt."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        # Ein Reagenz entfernen
        valid_experiment_profile["parameters"]["reagents"] = [
            r for r in valid_experiment_profile["parameters"]["reagents"]
            if r["reagent_name"] != "fecl3"
        ]
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        result = executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        assert result.success is False
        assert "fecl3" in result.error_message
    
    def test_validate_concentration_out_of_range(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Konzentration außerhalb Range wird erkannt."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        # Ascorbic Acid Konzentration außerhalb des Bereichs [1.0, 50.0]
        valid_experiment_profile["parameters"]["reagents"][0]["concentration_mm"] = 100.0
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        result = executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        assert result.success is False
        assert "ascorbic_acid" in result.error_message
    
    def test_build_job_payload_applies_defaults(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Defaults werden angewendet."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        result = executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        if result.success:
            queue_path = temp_workspace / "03_Hardware_Queue" / "experiment.json"
            job_payload = json.loads(queue_path.read_text(encoding="utf-8"))
            
            # Defaults sollten angewendet worden sein
            assert "excitation_wavelength_nm" in job_payload["parameters"]
            assert job_payload["parameters"]["excitation_wavelength_nm"] == 490
            assert "station_4_action" in job_payload
            assert job_payload["station_4_action"] == "FLUORESCENCE"
    
    def test_write_experiment_json_creates_file(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """experiment.json wird erstellt."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        result = executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        if result.success:
            queue_path = temp_workspace / "03_Hardware_Queue" / "experiment.json"
            assert queue_path.exists()
            assert "experiment.json" in result.output_files
    
    def test_write_experiment_json_is_atomic(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Keine .tmp-Datei nach Abschluss."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        executor.execute(temp_workspace / "02_Research_Cycles" / "Cycle_001")
        
        queue_path = temp_workspace / "03_Hardware_Queue" / "experiment.json"
        temp_path = queue_path.with_suffix(".json.tmp")
        assert not temp_path.exists()
    
    def test_execute_full_flow(self, temp_workspace, hardware_profile_path, valid_experiment_profile):
        """Vollständiger Ablauf von Profil → Validierung → Queue."""
        if hardware_profile_path is None:
            pytest.skip("Hardware-Profil nicht gefunden")
        
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(yaml.dump(valid_experiment_profile), encoding="utf-8")
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        result = executor.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_written == 1
        assert "job_id" in result.extra_data
        assert "queue_path" in result.extra_data
        
        # experiment.json sollte existieren
        queue_path = Path(result.extra_data["queue_path"])
        assert queue_path.exists()
        
        job_payload = json.loads(queue_path.read_text(encoding="utf-8"))
        assert "job_id" in job_payload
        assert job_payload["cycle_id"] == "Cycle_001"

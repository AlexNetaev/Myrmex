"""
Tests für die Hardware-Profil-Integration im Executor.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml

from src.castes.executor import ExecutorCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace mit hardware_profiles/."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()

    # Benötigte Verzeichnisse
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "03_Hardware_Queue").mkdir(parents=True)
    (workspace_path / "hardware_profiles").mkdir(parents=True)

    yield workspace_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def hardware_profile(temp_workspace):
    """Erstellt ein Hardware-Profil im Workspace."""
    profile_path = temp_workspace / "hardware_profiles" / "orbus_dummy_v2.yaml"
    
    profile = {
        "metadata": {
            "name": "OrbusSim Dummy V2",
            "version": "2.0.0",
            "description": "5-Stationen Karussell für Fenton-Experimente",
            "experiment_type": "fenton_fluorescence",
        },
        "limits": {
            "target_temperature_c": {"min": 20.0, "max": 75.0},
            "mixing_speed_rpm": {"min": 0, "max": 2000},
        },
        "defaults": {
            "excitation_wavelength_nm": 490,
            "emission_wavelength_nm": 520,
            "station_4_action": "FLUORESCENCE",
        },
    }
    
    profile_path.write_text(yaml.dump(profile), encoding="utf-8")
    return profile_path


class TestExecutorHardwareProfile:
    """Tests für die Hardware-Profil-Integration."""

    def test_load_hardware_profile_success(self, temp_workspace, hardware_profile):
        """Hardware-Profil wird erfolgreich geladen."""
        executor = ExecutorCaste(workspace_path=temp_workspace)
        
        profile = executor._load_hardware_profile()
        
        assert profile is not None
        assert profile["metadata"]["name"] == "OrbusSim Dummy V2"
        assert profile["metadata"]["version"] == "2.0.0"

    def test_load_hardware_profile_missing_directory(self, temp_workspace):
        """Fehlendes hardware_profiles/-Verzeichnis wird gemeldet."""
        # Lösche das Verzeichnis
        hardware_profiles_dir = temp_workspace / "hardware_profiles"
        shutil.rmtree(hardware_profiles_dir)
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        
        profile = executor._load_hardware_profile()
        
        assert profile is None

    def test_load_hardware_profile_empty_directory(self, temp_workspace):
        """Leeres hardware_profiles/-Verzeichnis wird gemeldet."""
        # Das Verzeichnis ist leer (kein YAML)
        executor = ExecutorCaste(workspace_path=temp_workspace)
        
        profile = executor._load_hardware_profile()
        
        assert profile is None

    def test_execute_with_hardware_profile(self, temp_workspace, hardware_profile):
        """Executor funktioniert mit Hardware-Profil."""
        # Verwende schnelle Version für Tests (kein Warten)
        executor = ExecutorCaste(workspace_path=temp_workspace)
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001" / "B_Hardware"
        work_dir.mkdir(parents=True)
        
        # Erstelle experiment_profile.yaml (erforderlich für execute)
        experiment_profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        experiment_profile_path.write_text(
            yaml.dump({
                "cycle_id": "Cycle_001",
                "parameters": {
                    "reagents": [
                        {"reagent_name": "ascorbic_acid", "concentration_mm": 10.0, "volume_ul": 500.0},
                        {"reagent_name": "fecl3", "concentration_mm": 1.0, "volume_ul": 100.0},
                        {"reagent_name": "h2o2", "concentration_mm": 10.0, "volume_ul": 200.0},
                        {"reagent_name": "fluorescein", "concentration_mm": 0.01, "volume_ul": 50.0},
                        {"reagent_name": "phosphate_buffer", "concentration_mm": 50.0, "volume_ul": 500.0},
                    ],
                    "mixing_speed_rpm": 500,
                    "mixing_time_s": 30,
                    "target_temperature_c": 25.0,
                    "heating_time_s": 60,
                    "measurement_interval_ms": 1000,
                    "fluorescence_duration_s": 60,
                },
            }),
            encoding="utf-8",
        )
        
        # Mock die Hardware-Ergebnisse - erstelle sie VOR dem Aufruf von _wait_for_hardware_results_fast
        measurement_csv_path = work_dir / "measurement.csv"
        measurement_csv_path.write_text(
            "time_ms,temp_c,fluorescence_raw_au\n"
            "0,22.0,100.0\n"
            "1000,25.0,95.0\n",
            encoding="utf-8",
        )
        
        hardware_protocol_path = work_dir / "hardware_protocol.json"
        hardware_protocol_path.write_text(
            '{"job_id": "Cycle_001", "status": "OK"}',
            encoding="utf-8",
        )
        
        # Überschreibe _wait_for_hardware_results um die existierenden Dateien zu verwenden
        def mock_wait(*args, **kwargs):
            return {
                "measurement_csv_path": measurement_csv_path,
                "hardware_protocol_path": hardware_protocol_path,
            }
        executor._wait_for_hardware_results = mock_wait
        
        result = executor.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_written == 1

    def test_execute_without_hardware_profile(self, temp_workspace):
        """Executor funktioniert ohne Hardware-Profil (Fallback)."""
        # Lösche das Verzeichnis
        hardware_profiles_dir = temp_workspace / "hardware_profiles"
        shutil.rmtree(hardware_profiles_dir)
        
        executor = ExecutorCaste(workspace_path=temp_workspace)
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001" / "B_Hardware"
        work_dir.mkdir(parents=True)
        
        # Erstelle experiment_profile.yaml (erforderlich für execute)
        experiment_profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        experiment_profile_path.write_text(
            yaml.dump({
                "cycle_id": "Cycle_001",
                "parameters": {
                    "reagents": [],
                    "mixing_speed_rpm": 500,
                    "mixing_time_s": 30,
                    "target_temperature_c": 25.0,
                    "heating_time_s": 60,
                    "measurement_interval_ms": 1000,
                    "fluorescence_duration_s": 60,
                },
            }),
            encoding="utf-8",
        )
        
        # Mock die Hardware-Ergebnisse
        measurement_csv_path = work_dir / "measurement.csv"
        measurement_csv_path.write_text(
            "time_ms,temp_c,fluorescence_raw_au\n"
            "0,22.0,100.0\n",
            encoding="utf-8",
        )
        
        hardware_protocol_path = work_dir / "hardware_protocol.json"
        hardware_protocol_path.write_text(
            '{"job_id": "Cycle_001", "status": "OK"}',
            encoding="utf-8",
        )
        
        # Überschreibe _wait_for_hardware_results um die existierenden Dateien zu verwenden
        def mock_wait(*args, **kwargs):
            return {
                "measurement_csv_path": measurement_csv_path,
                "hardware_protocol_path": hardware_protocol_path,
            }
        executor._wait_for_hardware_results = mock_wait
        
        result = executor.execute(work_dir)
        
        # Sollte erfolgreich sein (Fallback)
        assert result.success is True
        assert result.pheromones_written == 1

    def test_workspace_manager_creates_hardware_profiles_directory(self, temp_workspace):
        """WorkspaceManager erstellt das hardware_profiles/-Verzeichnis."""
        from src.workspace.workspace_manager import WorkspaceManager
        
        wm = WorkspaceManager(workspace_root=temp_workspace)
        wm.initialize()
        
        hardware_profiles_dir = temp_workspace / "hardware_profiles"
        assert hardware_profiles_dir.exists()
        assert hardware_profiles_dir.is_dir()

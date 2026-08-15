"""Tests für die SimulatorCaste."""
import pytest
from pathlib import Path
import tempfile
import shutil
import csv
import yaml

from src.castes.simulator import SimulatorCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


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
def simulator(temp_workspace):
    """Erstellt eine SimulatorCaste mit temporärem Workspace."""
    return SimulatorCaste(workspace_path=temp_workspace)


class TestSimulatorCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_simulator(self):
        assert SimulatorCaste.caste_name == CasteName.SIMULATOR
    
    def test_reads_trail_pheromones(self):
        assert PheromoneType.TRAIL in SimulatorCaste.reads_pheromones
    
    def test_writes_trail_pheromones(self):
        assert PheromoneType.TRAIL in SimulatorCaste.writes_pheromones


class TestSimulatorExecution:
    """Tests für die Ausführung der SimulatorCaste."""
    
    def test_execute_writes_sim_data_csv(self, simulator, temp_workspace):
        """execute() schreibt eine sim_data.csv."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = simulator.execute(work_dir)
        
        assert result.success is True
        sim_data_path = work_dir / "sim_data.csv"
        assert sim_data_path.exists()
    
    def test_execute_writes_trail_pheromone(self, simulator, temp_workspace):
        """execute() schreibt ein TRAIL-Pheromon."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = simulator.execute(work_dir)
        
        assert result.success is True
        assert result.pheromones_written == 1
    
    def test_execute_uses_defaults_without_profile(self, simulator, temp_workspace):
        """Ohne Profil werden Defaults genutzt."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = simulator.execute(work_dir)
        
        assert result.success is True
        # Sollte trotzdem funktionieren und Daten erzeugen
        sim_data_path = work_dir / "sim_data.csv"
        assert sim_data_path.exists()
    
    def test_execute_reads_profile_params(self, simulator, temp_workspace):
        """Mit Profil werden die Parameter übernommen."""
        # Erstelle ein Profil mit spezifischen Parametern
        profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
        profile = {
            "experiment_type": "fenton_fluorescence",
            "parameters": {
                "target_temperature_c": 50.0,
                "fluorescence_duration_s": 30.0,
                "measurement_interval_ms": 1000,
                "fluorescein_concentration_mm": 0.015,
            },
        }
        profile_path.write_text(yaml.dump(profile), encoding="utf-8")
        
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = simulator.execute(work_dir)
        
        assert result.success is True
        
        # Überprüfe die sim_data.csv auf korrekte Werte
        sim_data_path = work_dir / "sim_data.csv"
        with sim_data_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Temperatur sollte sich 50°C annähern
        last_temp = float(rows[-1]["temp_c"])
        assert last_temp > 40.0  # Sollte nahe an 50 sein
    
    def test_sim_data_csv_has_correct_columns(self, simulator, temp_workspace):
        """Die CSV hat die Spalten time_ms, temp_c, ph, fluorescence_au."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        simulator.execute(work_dir)
        
        sim_data_path = work_dir / "sim_data.csv"
        with sim_data_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        required_columns = {"time_ms", "temp_c", "ph", "fluorescence_au"}
        assert set(rows[0].keys()) == required_columns
    
    def test_sim_data_csv_values_plausible(self, simulator, temp_workspace):
        """Die Werte sind physikalisch plausibel (Temp steigt, pH sinkt)."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        simulator.execute(work_dir)
        
        sim_data_path = work_dir / "sim_data.csv"
        with sim_data_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) > 1
        
        # Temperatur sollte steigen (von ambient zu target)
        first_temp = float(rows[0]["temp_c"])
        last_temp = float(rows[-1]["temp_c"])
        assert first_temp < last_temp
        
        # pH sollte sinken
        first_ph = float(rows[0]["ph"])
        last_ph = float(rows[-1]["ph"])
        assert first_ph > last_ph
        
        # Zeit sollte monoton steigen
        for i in range(1, len(rows)):
            assert float(rows[i]["time_ms"]) > float(rows[i-1]["time_ms"])
    
    def test_result_contains_metadata(self, simulator, temp_workspace):
        """Das Ergebnis enthält Metadaten."""
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)
        
        result = simulator.execute(work_dir)
        
        assert "sim_data_path" in result.extra_data
        assert "num_points" in result.extra_data
        assert "pheromone_id" in result.extra_data
        assert result.extra_data["num_points"] > 0

"""
Tests für den Hardware-Dummy.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from orbus_dummy_v2.models.experiment import ExperimentJob, MeasurementResult
from orbus_dummy_v2.physics.preparation import PreparationPhysics
from orbus_dummy_v2.physics.measurement import MeasurementPhysics
from orbus_dummy_v2.io.result_writer import ResultWriter


@pytest.fixture
def temp_output_dir():
    """Erstellt ein temporäres Output-Verzeichnis."""
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir) / "output"
    output_dir.mkdir()
    yield output_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestPreparationPhysics:
    """Tests für die Preparation-Physik."""
    
    def test_valid_preparation(self):
        """Valide Preparation gibt OK zurück."""
        physics = PreparationPhysics()
        params = {
            "reagents": [{"name": "A", "volume_ml": 1.0}],
            "mixing_time_s": 10.0
        }
        result = physics.simulate(params)
        assert result["status"] == "OK"
    
    def test_no_reagents(self):
        """Preparation ohne Reagenzien gibt ERROR zurück."""
        physics = PreparationPhysics()
        params = {"reagents": [], "mixing_time_s": 10.0}
        result = physics.simulate(params)
        assert result["status"] == "ERROR"


class TestMeasurementPhysics:
    """Tests für die Measurement-Physik."""
    
    def test_measurement_produces_data(self):
        """Measurement produziert Datenpunkte."""
        physics = MeasurementPhysics(seed=42)
        params = {
            "duration_s": 10.0,
            "interval_ms": 1000,
            "target_temperature_c": 30.0
        }
        results = physics.simulate(params)
        assert len(results) > 0
        assert all(isinstance(r, MeasurementResult) for r in results)
    
    def test_measurement_reproducible_with_seed(self):
        """Measurement mit gleichem Seed ist reproduzierbar."""
        params = {"duration_s": 5.0, "interval_ms": 1000, "target_temperature_c": 25.0}
        
        physics1 = MeasurementPhysics(seed=123)
        results1 = physics1.simulate(params)
        
        physics2 = MeasurementPhysics(seed=123)
        results2 = physics2.simulate(params)
        
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.time_ms == r2.time_ms
            assert r1.temp_c == r2.temp_c
            assert r1.fluorescence_au == r2.fluorescence_au


class TestResultWriter:
    """Tests für den Result-Writer."""
    
    def test_write_measurement_csv(self, temp_output_dir):
        """CSV wird korrekt geschrieben."""
        writer = ResultWriter(temp_output_dir)
        measurements = [
            MeasurementResult(time_ms=0, temp_c=20.0, fluorescence_au=100.0),
            MeasurementResult(time_ms=1000, temp_c=21.0, fluorescence_au=99.5),
        ]
        
        csv_path = writer.write_measurement_csv(measurements)
        assert csv_path.exists()
        
        content = csv_path.read_text()
        assert "time_ms,temp_c,fluorescence_au" in content
        assert "0,20.0,100.0" in content
    
    def test_write_hardware_protocol(self, temp_output_dir):
        """Protocol-JSON wird korrekt geschrieben."""
        writer = ResultWriter(temp_output_dir)
        job = ExperimentJob(
            job_id="test_job",
            cycle_id="Cycle_001",
            preparation_params={"reagents": [{"name": "A"}], "mixing_time_s": 10.0},
            measurement_params={"duration_s": 5.0, "interval_ms": 1000, "target_temperature_c": 25.0}
        )
        prep_result = {"status": "OK"}
        measurements = [
            MeasurementResult(time_ms=0, temp_c=20.0, fluorescence_au=100.0),
            MeasurementResult(time_ms=1000, temp_c=21.0, fluorescence_au=99.5),
        ]
        
        protocol_path = writer.write_hardware_protocol(job, prep_result, measurements)
        assert protocol_path.exists()
        
        import json
        protocol = json.loads(protocol_path.read_text())
        assert protocol["job_id"] == "test_job"
        assert protocol["status"] == "OK"
        assert "achieved_parameters" in protocol

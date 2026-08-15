"""
tests/test_hardware_integration.py
Integrationstests zwischen Myrmex und dem Hardware-Dummy.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import json
import subprocess
import sys
import os
import time


@pytest.fixture
def integration_workspace():
    """Erstellt einen temporären Workspace für Integrationstests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # Alle benötigten Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "02_Research_Cycles").mkdir(parents=True)
    (workspace_path / "03_Hardware_Queue").mkdir(parents=True)
    (workspace_path / "04_Knowledge_Base").mkdir(parents=True)
    (workspace_path / "05_Loops").mkdir(parents=True)
    
    yield workspace_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestHardwareIntegration:
    """Integrationstests zwischen Myrmex und Dummy."""
    
    def test_dummy_processes_experiment_json(self, integration_workspace):
        """
        Testet, dass der Dummy experiment.json verarbeitet.
        """
        # 1. Schreibe experiment.json in die Queue
        hardware_queue_dir = integration_workspace / "03_Hardware_Queue"
        experiment_json_path = hardware_queue_dir / "experiment.json"
        
        experiment_json = {
            "job_id": "test_job_001",
            "cycle_id": "Cycle_001",
            "preparation_params": {
                "reagents": [{"name": "A", "volume_ml": 1.0}],
                "mixing_time_s": 10.0
            },
            "measurement_params": {
                "duration_s": 2.0,  # Kurz für den Test
                "interval_ms": 500,
                "target_temperature_c": 30.0
            },
            "simulation_seed": 42
        }
        
        experiment_json_path.write_text(json.dumps(experiment_json, indent=2), encoding="utf-8")
        
        # 2. Starte den Dummy-Daemon (kurzzeitig)
        dummy_script = Path(__file__).parent.parent / "dummy_daemon.py"
        
        if not dummy_script.exists():
            pytest.skip(f"Dummy script not found at {dummy_script}")
        
        # Starte den Dummy als separaten Prozess
        process = subprocess.Popen(
            [sys.executable, str(dummy_script)],
            env={
                "MYRMEX_WORKSPACE": str(integration_workspace),
                **dict(os.environ)
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Warte kurz, damit der Dummy den Job verarbeiten kann
        time.sleep(4.0)
        
        # Beende den Dummy
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
        # 3. Prüfe, dass die Ergebnisse geschrieben wurden
        hardware_dir = integration_workspace / "02_Research_Cycles" / "Cycle_001" / "B_Hardware"
        measurement_csv_path = hardware_dir / "measurement.csv"
        hardware_protocol_path = hardware_dir / "hardware_protocol.json"
        
        assert measurement_csv_path.exists(), "measurement.csv wurde nicht erstellt"
        assert hardware_protocol_path.exists(), "hardware_protocol.json wurde nicht erstellt"
        
        # Prüfe den Inhalt des Protokolls
        protocol = json.loads(hardware_protocol_path.read_text(encoding="utf-8"))
        assert protocol["status"] == "OK"
        assert protocol["job_id"] == "test_job_001"
    
    def test_estop_handling(self, integration_workspace):
        """
        Testet, dass der Dummy auf E-Stop reagiert.
        """
        # 1. Aktiviere den E-Stop
        estop_flag = integration_workspace / "00_System" / "ESTOP.flag"
        estop_flag.write_text("E-Stop activated for testing", encoding="utf-8")
        
        # 2. Schreibe experiment.json in die Queue
        hardware_queue_dir = integration_workspace / "03_Hardware_Queue"
        experiment_json_path = hardware_queue_dir / "experiment.json"
        
        experiment_json = {
            "job_id": "test_job_002",
            "cycle_id": "Cycle_001",
            "preparation_params": {
                "reagents": [{"name": "A", "volume_ml": 1.0}],
                "mixing_time_s": 10.0
            },
            "measurement_params": {
                "duration_s": 2.0,
                "interval_ms": 500,
                "target_temperature_c": 25.0
            },
            "simulation_seed": 42
        }
        
        experiment_json_path.write_text(json.dumps(experiment_json, indent=2), encoding="utf-8")
        
        # 3. Starte den Dummy-Daemon (kurzzeitig)
        dummy_script = Path(__file__).parent.parent / "dummy_daemon.py"
        
        if not dummy_script.exists():
            pytest.skip(f"Dummy script not found at {dummy_script}")
        
        process = subprocess.Popen(
            [sys.executable, str(dummy_script)],
            env={
                "MYRMEX_WORKSPACE": str(integration_workspace),
                **dict(os.environ)
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Warte kurz - der Dummy sollte auf E-Stop warten
        time.sleep(3.0)
        
        # Beende den Dummy
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
        # 4. Prüfe, dass der E-Stop erkannt wurde
        # Der Job sollte NICHT verarbeitet worden sein, da E-Stop aktiv war
        hardware_dir = integration_workspace / "02_Research_Cycles" / "Cycle_001" / "B_Hardware"
        hardware_protocol_path = hardware_dir / "hardware_protocol.json"
        
        # Da E-Stop aktiv war, sollte entweder kein Protokoll existieren
        # oder ein ESTOP-Protokoll (wenn der Job schon gestartet war)
        # In diesem Fall sollte kein Protokoll existieren, da der Daemon
        # vor dem Warten auf den Job den E-Stop prüft
        if hardware_protocol_path.exists():
            protocol = json.loads(hardware_protocol_path.read_text(encoding="utf-8"))
            # Wenn ein Protokoll existiert, muss es ESTOP-Status haben
            assert protocol["status"] == "ESTOP"
        else:
            # Kein Protokoll bedeutet auch, dass E-Stop funktioniert hat
            # (Job wurde nicht ausgeführt)
            pass
    
    def test_error_handling_invalid_params(self, integration_workspace):
        """
        Testet, dass der Dummy Fehler bei invaliden Parametern behandelt.
        """
        # 1. Schreibe experiment.json mit invaliden Parametern in die Queue
        hardware_queue_dir = integration_workspace / "03_Hardware_Queue"
        experiment_json_path = hardware_queue_dir / "experiment.json"
        
        experiment_json = {
            "job_id": "test_job_003",
            "cycle_id": "Cycle_001",
            "preparation_params": {
                "reagents": [],  # Keine Reagenzien -> ERROR
                "mixing_time_s": 10.0
            },
            "measurement_params": {
                "duration_s": 2.0,
                "interval_ms": 500,
                "target_temperature_c": 25.0
            },
            "simulation_seed": 42
        }
        
        experiment_json_path.write_text(json.dumps(experiment_json, indent=2), encoding="utf-8")
        
        # 2. Starte den Dummy-Daemon (kurzzeitig)
        dummy_script = Path(__file__).parent.parent / "dummy_daemon.py"
        
        if not dummy_script.exists():
            pytest.skip(f"Dummy script not found at {dummy_script}")
        
        process = subprocess.Popen(
            [sys.executable, str(dummy_script)],
            env={
                "MYRMEX_WORKSPACE": str(integration_workspace),
                **dict(os.environ)
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Warte kurz, damit der Dummy den Job verarbeiten kann
        time.sleep(4.0)
        
        # Beende den Dummy
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
        # 3. Prüfe, dass ein Fehler-Protokoll geschrieben wurde
        hardware_dir = integration_workspace / "02_Research_Cycles" / "Cycle_001" / "B_Hardware"
        hardware_protocol_path = hardware_dir / "hardware_protocol.json"
        
        assert hardware_protocol_path.exists(), "hardware_protocol.json wurde nicht erstellt"
        
        # Prüfe den Inhalt des Protokolls
        protocol = json.loads(hardware_protocol_path.read_text(encoding="utf-8"))
        assert protocol["status"] == "ERROR"
        assert protocol["job_id"] == "test_job_003"
        assert protocol["hardware_faults_detected"] == True

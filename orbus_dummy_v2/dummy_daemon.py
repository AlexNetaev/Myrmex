"""
Haupt-Daemon für den Hardware-Dummy.
Pollt die Queue und führt Jobs aus.
Erweitert um E-Stop-Handling und robuste Fehlerbehandlung.
"""
import sys
from pathlib import Path
import logging
import time
import json
from datetime import datetime, timezone

# Füge Parent-Verzeichnis zum Path hinzu, damit Imports funktionieren
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbus_dummy_v2.config import DUMMY_CONFIG
from orbus_dummy_v2.io.queue_watcher import QueueWatcher
from orbus_dummy_v2.io.result_writer import ResultWriter
from orbus_dummy_v2.physics.preparation import PreparationPhysics
from orbus_dummy_v2.physics.measurement import MeasurementPhysics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dummy_daemon")


def check_estop(workspace_root: Path) -> bool:
    """
    Prüft, ob der E-Stop aktiv ist.
    
    Args:
        workspace_root: Pfad zum Workspace-Root.
    
    Returns:
        True wenn der E-Stop aktiv ist, sonst False.
    """
    estop_flag = workspace_root / "00_System" / "ESTOP.flag"
    return estop_flag.exists()


def handle_estop(workspace_root: Path, job_id: str, cycle_id: str = "Cycle_001") -> None:
    """
    Behandelt den E-Stop während eines Jobs.
    
    Schreibt ein Fehler-Protokoll und bricht den Job ab.
    """
    logger.critical(f"[Dummy] E-STOP ACTIVE! Aborting job {job_id}")
    
    # Schreibe ein Fehler-Protokoll
    output_dir = workspace_root / "02_Research_Cycles" / cycle_id / "B_Hardware"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    protocol_path = output_dir / "hardware_protocol.json"
    
    protocol = {
        "job_id": job_id,
        "cycle_id": cycle_id,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "simulator_name": "OrbusSim Dummy V2",
        "simulator_version": "2.0.0-minimal",
        "status": "ESTOP",
        "total_execution_time_s": 0.0,
        "hardware_faults_detected": True,
        "fault_details": ["E-Stop activated by operator"],
        "target_parameters": {},
        "achieved_parameters": {},
        "stations_log": {},
        "output_files": []
    }
    
    protocol_path.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    logger.critical(f"[Dummy] Wrote ESTOP protocol to {protocol_path}")


def _write_error_protocol(job, prep_result: dict, output_dir: Path) -> None:
    """
    Schreibt ein Fehler-Protokoll.
    
    Args:
        job: Der ursprüngliche ExperimentJob.
        prep_result: Das Ergebnis der Preparation.
        output_dir: Das Output-Verzeichnis.
    """
    protocol_path = output_dir / "hardware_protocol.json"
    
    protocol = {
        "job_id": job.job_id,
        "cycle_id": job.cycle_id,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "simulator_name": "OrbusSim Dummy V2",
        "simulator_version": "2.0.0-minimal",
        "status": "ERROR",
        "total_execution_time_s": 0.0,
        "hardware_faults_detected": True,
        "fault_details": [prep_result.get("message", "Unknown error")],
        "target_parameters": {
            "target_temperature_c": job.measurement_params.get("target_temperature_c", 25.0),
            "mixing_time_s": job.preparation_params.get("mixing_time_s", 10.0),
        },
        "achieved_parameters": {},
        "stations_log": {
            "station_1_preparation": prep_result,
            "station_2_measurement": {"status": "SKIPPED"}
        },
        "simulation_seed": job.simulation_seed,
        "output_files": ["hardware_protocol.json"]
    }
    
    protocol_path.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    logger.error(f"[Dummy] Wrote error protocol to {protocol_path}")


def execute_job(job) -> None:
    """
    Führt einen einzelnen Job aus.
    
    Args:
        job: ExperimentJob-Objekt.
    """
    logger.info(f"[Dummy] Executing job {job.job_id} for {job.cycle_id}")
    
    # Output-Verzeichnis bestimmen
    output_dir = DUMMY_CONFIG["workspace_root"] / "02_Research_Cycles" / job.cycle_id / "B_Hardware"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Physik-Modelle initialisieren
        prep_physics = PreparationPhysics(seed=job.simulation_seed)
        meas_physics = MeasurementPhysics(seed=job.simulation_seed)
        
        # Station 1: Preparation
        logger.info("[Dummy] Station 1: Preparation")
        prep_result = prep_physics.simulate(job.preparation_params)
        
        if prep_result.get("status") != "OK":
            logger.error(f"[Dummy] Preparation failed: {prep_result}")
            _write_error_protocol(job, prep_result, output_dir)
            return
        
        # Station 2: Measurement
        logger.info("[Dummy] Station 2: Measurement")
        measurements = meas_physics.simulate(job.measurement_params)
        
        if not measurements:
            logger.error("[Dummy] Measurement produced no data")
            _write_error_protocol(job, prep_result, output_dir)
            return
        
        # Ergebnisse schreiben
        logger.info(f"[Dummy] Writing {len(measurements)} measurement points")
        writer = ResultWriter(output_dir)
        writer.write_measurement_csv(measurements)
        writer.write_hardware_protocol(job, prep_result, measurements, status="OK")
        
        logger.info(f"[Dummy] Job {job.job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"[Dummy] Job {job.job_id} failed with error: {e}", exc_info=True)
        _write_error_protocol(job, {"status": "ERROR", "message": str(e)}, output_dir)


def main():
    """Haupt-Schleife des Dummy-Daemons."""
    logger.info("[Dummy] Starting OrbusSim Dummy V2 (minimal version)")
    
    # Workspace-Root bestimmen
    workspace_root = DUMMY_CONFIG["workspace_root"]
    logger.info(f"[Dummy] Workspace: {workspace_root}")
    logger.info(f"[Dummy] Queue: {DUMMY_CONFIG['queue_dir']}")
    
    watcher = QueueWatcher(
        queue_dir=DUMMY_CONFIG["queue_dir"],
        poll_interval_s=DUMMY_CONFIG["poll_interval_s"]
    )
    
    logger.info("[Dummy] Waiting for jobs...")
    
    while True:
        try:
            # Prüfe E-Stop BEVOR wir einen neuen Job starten
            if check_estop(workspace_root):
                logger.critical("[Dummy] E-STOP ACTIVE! Waiting for release...")
                while check_estop(workspace_root):
                    time.sleep(1.0)
                logger.info("[Dummy] E-Stop released. Resuming...")
                continue
            
            job = watcher.wait_for_job()
            
            # Prüfe E-Stop NACHDEM wir einen Job gefunden haben
            if check_estop(workspace_root):
                handle_estop(workspace_root, job.job_id, job.cycle_id)
                watcher.archive_job(job.job_id)
                continue
            
            execute_job(job)
            watcher.archive_job(job.job_id)
            
        except KeyboardInterrupt:
            logger.info("[Dummy] Shutting down (Ctrl+C)")
            break
        except Exception as e:
            logger.error(f"[Dummy] Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    main()

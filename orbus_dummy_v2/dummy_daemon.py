"""
Haupt-Daemon für den Hardware-Dummy.
Pollt die Queue und führt Jobs aus.
"""
import sys
from pathlib import Path
import logging

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


def execute_job(job) -> None:
    """
    Führt einen einzelnen Job aus.
    
    Args:
        job: ExperimentJob-Objekt.
    """
    logger.info(f"[Dummy] Executing job {job.job_id} for {job.cycle_id}")
    
    # Output-Verzeichnis bestimmen
    # Erwartet: 02_Research_Cycles/Cycle_XXX/B_Hardware/
    output_dir = DUMMY_CONFIG["workspace_root"] / "02_Research_Cycles" / job.cycle_id / "B_Hardware"
    
    # Physik-Modelle initialisieren
    prep_physics = PreparationPhysics(seed=job.simulation_seed)
    meas_physics = MeasurementPhysics(seed=job.simulation_seed)
    
    # Station 1: Preparation
    logger.info("[Dummy] Station 1: Preparation")
    prep_result = prep_physics.simulate(job.preparation_params)
    
    if prep_result.get("status") != "OK":
        logger.error(f"[Dummy] Preparation failed: {prep_result}")
        # Trotzdem Protocol schreiben, aber mit ERROR-Status
        writer = ResultWriter(output_dir)
        writer.write_hardware_protocol(job, prep_result, [], status="ERROR")
        return
    
    # Station 2: Measurement
    logger.info("[Dummy] Station 2: Measurement")
    measurements = meas_physics.simulate(job.measurement_params)
    
    if not measurements:
        logger.error("[Dummy] Measurement produced no data")
        writer = ResultWriter(output_dir)
        writer.write_hardware_protocol(job, prep_result, [], status="ERROR")
        return
    
    # Ergebnisse schreiben
    logger.info(f"[Dummy] Writing {len(measurements)} measurement points")
    writer = ResultWriter(output_dir)
    writer.write_measurement_csv(measurements)
    writer.write_hardware_protocol(job, prep_result, measurements, status="OK")
    
    logger.info(f"[Dummy] Job {job.job_id} completed successfully")


def main():
    """Haupt-Schleife des Dummy-Daemons."""
    logger.info("[Dummy] Starting OrbusSim Dummy V2 (minimal version)")
    logger.info(f"[Dummy] Workspace: {DUMMY_CONFIG['workspace_root']}")
    logger.info(f"[Dummy] Queue: {DUMMY_CONFIG['queue_dir']}")
    
    watcher = QueueWatcher(
        queue_dir=DUMMY_CONFIG["queue_dir"],
        poll_interval_s=DUMMY_CONFIG["poll_interval_s"]
    )
    
    logger.info("[Dummy] Waiting for jobs...")
    
    while True:
        try:
            job = watcher.wait_for_job()
            execute_job(job)
            watcher.archive_job(job.job_id)
        except KeyboardInterrupt:
            logger.info("[Dummy] Shutting down (Ctrl+C)")
            break
        except Exception as e:
            logger.error(f"[Dummy] Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    main()

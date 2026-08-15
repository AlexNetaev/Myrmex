"""
Pollt die Hardware-Queue auf neue Jobs.
"""
import json
import time
from pathlib import Path
from typing import Optional
from ..models.experiment import ExperimentJob


class QueueWatcher:
    """
    Pollt die Hardware-Queue und gibt neue Jobs zurück.
    """
    
    def __init__(self, queue_dir: Path, poll_interval_s: float = 1.0):
        """
        Args:
            queue_dir: Pfad zur Hardware-Queue (03_Hardware_Queue/).
            poll_interval_s: Poll-Intervall in Sekunden.
        """
        self.queue_dir = queue_dir
        self.poll_interval_s = poll_interval_s
        self.experiment_file = queue_dir / "experiment.json"
    
    def poll(self) -> Optional[ExperimentJob]:
        """
        Pollt einmal auf einen neuen Job.
        
        Returns:
            ExperimentJob wenn vorhanden, sonst None.
        """
        if not self.experiment_file.exists():
            return None
        
        try:
            data = json.loads(self.experiment_file.read_text(encoding="utf-8"))
            job = ExperimentJob.model_validate(data)
            return job
        except Exception as e:
            print(f"[QueueWatcher] Failed to parse experiment.json: {e}")
            return None
    
    def wait_for_job(self) -> ExperimentJob:
        """
        Wartet blockierend auf einen neuen Job.
        
        Returns:
            ExperimentJob wenn gefunden.
        """
        while True:
            job = self.poll()
            if job is not None:
                return job
            time.sleep(self.poll_interval_s)
    
    def archive_job(self, job_id: str) -> None:
        """
        Verschiebt den Job in _processed/ nach erfolgreicher Ausführung.
        
        Args:
            job_id: Die Job-ID.
        """
        processed_dir = self.queue_dir / "_processed"
        processed_dir.mkdir(exist_ok=True)
        
        processed_file = processed_dir / f"{job_id}.json"
        self.experiment_file.rename(processed_file)

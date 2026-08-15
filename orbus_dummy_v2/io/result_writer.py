"""
Schreibt Messergebnisse und Hardware-Protokoll.
"""
import json
import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from ..models.experiment import ExperimentJob, MeasurementResult


class ResultWriter:
    """
    Schreibt measurement.csv und hardware_protocol.json.
    """
    
    def __init__(self, output_dir: Path):
        """
        Args:
            output_dir: Ausgabe-Verzeichnis (z.B. 02_Research_Cycles/Cycle_001/B_Hardware/).
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_measurement_csv(self, measurements: list[MeasurementResult]) -> Path:
        """
        Schreibt die Messergebnisse als CSV.
        
        Args:
            measurements: Liste von MeasurementResult-Objekten.
        
        Returns:
            Pfad zur geschriebenen CSV-Datei.
        """
        csv_path = self.output_dir / "measurement.csv"
        
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["time_ms", "temp_c", "fluorescence_au"]
            )
            writer.writeheader()
            for m in measurements:
                writer.writerow({
                    "time_ms": m.time_ms,
                    "temp_c": m.temp_c,
                    "fluorescence_au": m.fluorescence_au
                })
        
        return csv_path
    
    def write_hardware_protocol(
        self,
        job: ExperimentJob,
        preparation_result: dict,
        measurements: list[MeasurementResult],
        status: str = "OK"
    ) -> Path:
        """
        Schreibt das Hardware-Protokoll als JSON.
        
        Args:
            job: Der ursprüngliche ExperimentJob.
            preparation_result: Ergebnis der Preparation-Station.
            measurements: Liste der Messergebnisse.
            status: Gesamtstatus ("OK" oder "ERROR").
        
        Returns:
            Pfad zur geschriebenen JSON-Datei.
        """
        protocol_path = self.output_dir / "hardware_protocol.json"
        
        # Statistiken berechnen
        if measurements:
            first_temp = measurements[0].temp_c
            last_temp = measurements[-1].temp_c
            first_fluor = measurements[0].fluorescence_au
            last_fluor = measurements[-1].fluorescence_au
            
            # Einfache lineare Regression für Fluoreszenz-Slope
            n = len(measurements)
            sum_t = sum(m.time_ms for m in measurements)
            sum_f = sum(m.fluorescence_au for m in measurements)
            sum_tf = sum(m.time_ms * m.fluorescence_au for m in measurements)
            sum_t2 = sum(m.time_ms ** 2 for m in measurements)
            
            denominator = n * sum_t2 - sum_t ** 2
            if denominator != 0:
                slope = (n * sum_tf - sum_t * sum_f) / denominator
                # Umrechnen von AU/ms in AU/s
                slope_au_per_s = slope * 1000.0
            else:
                slope_au_per_s = 0.0
        else:
            first_temp = last_temp = 0.0
            first_fluor = last_fluor = 0.0
            slope_au_per_s = 0.0
        
        protocol = {
            "job_id": job.job_id,
            "cycle_id": job.cycle_id,
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "simulator_name": "OrbusSim Dummy V2",
            "simulator_version": "2.0.0-minimal",
            "status": status,
            "total_execution_time_s": 0.0,  # Dummy, keine echte Zeitmessung
            "hardware_faults_detected": status != "OK",
            "fault_details": [] if status == "OK" else ["Simulation error"],
            "target_parameters": {
                "target_temperature_c": job.measurement_params.get("target_temperature_c", 25.0),
                "mixing_time_s": job.preparation_params.get("mixing_time_s", 10.0),
                "measurement_duration_s": job.measurement_params.get("duration_s", 60.0),
                "measurement_interval_ms": job.measurement_params.get("interval_ms", 1000)
            },
            "achieved_parameters": {
                "mean_temperature_c": (first_temp + last_temp) / 2.0 if measurements else 0.0,
                "final_temperature_c": last_temp,
                "fluorescence_raw_initial_au": first_fluor,
                "fluorescence_raw_final_au": last_fluor,
                "fluorescence_raw_slope_au_per_s": slope_au_per_s,
                "temperature_points": len(measurements),
                "fluorescence_points": len(measurements)
            },
            "stations_log": {
                "station_1_preparation": preparation_result,
                "station_2_measurement": {
                    "status": "OK" if measurements else "ERROR",
                    "data_points": len(measurements)
                }
            },
            "simulation_seed": job.simulation_seed,
            "calibration_loaded": False,
            "output_files": ["measurement.csv", "hardware_protocol.json"]
        }
        
        protocol_path.write_text(
            json.dumps(protocol, indent=2),
            encoding="utf-8"
        )
        
        return protocol_path

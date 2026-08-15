"""
src/castes/simulator.py
Die SimulatorCaste — der digitale Zwilling.

Ersetzt die PlaceholderCaste für die SIMULATE-Aktion. Sie liest das
experiment_profile.yaml (vom Planner erzeugt), simuliert die Zeitreihe
mit den deterministischen physikalischen Modellen aus sim_models.py,
schreibt sim_data.csv, und legt ein TRAIL-Pheromon mit der
Simulations-Zusammenfassung ab.

Die SimulatorCaste ist rein deterministisch (kein LLM), damit sie
schnell, günstig und testbar ist.
"""
from __future__ import annotations
import csv
import logging
from pathlib import Path

import yaml

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.castes import sim_models
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType

logger = logging.getLogger("caste.simulator")


class SimulatorCaste(BaseCaste):
    """
    Die SimulatorCaste — simuliert das Experiment und erzeugt sim_data.csv.
    """
    
    caste_name = CasteName.SIMULATOR
    role = "Das Experiment simulieren (digitaler Zwilling)"
    specialization = "Deterministische Zeitreihen-Simulation"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]
    
    EXPERIMENT_PROFILE_FILENAME = "experiment_profile.yaml"
    SIM_DATA_FILENAME = "sim_data.csv"
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Simulation aus:
        1. Liest das experiment_profile.yaml (oder nutzt Defaults).
        2. Simuliert die Zeitreihe mit sim_models.generate_time_series.
        3. Schreibt sim_data.csv.
        4. Schreibt ein TRAIL-Pheromon mit der Simulations-Zusammenfassung.
        """
        self.logger.info("[%s] Starting simulation", self.caste_name.value)
        
        # 1. Parameter laden (aus experiment_profile.yaml oder Defaults)
        params = self._load_simulation_params()
        
        # 2. Zeitreihe simulieren
        series = sim_models.generate_time_series(
            duration_s=params["fluorescence_duration_s"],
            interval_ms=params["measurement_interval_ms"],
            target_temp_c=params["target_temperature_c"],
            ph_start=params["ph_start"],
            delta_ph=params["delta_ph"],
            k_ph=params["k_ph"],
            pka=params["pka"],
            fluor_conc_um=params["fluor_conc_um"],
        )
        
        if not series:
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=False,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                error_message="Simulation produced an empty time series",
            )
        
        # 3. sim_data.csv schreiben
        sim_data_path = work_dir / self.SIM_DATA_FILENAME
        self._write_sim_data(sim_data_path, series)
        
        # 4. TRAIL-Pheromon mit Zusammenfassung schreiben
        summary = self._build_simulation_summary(series)
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=summary,
            tags=["simulation", "digital_twin"],
            strength=0.5,
            relevance=0.6,
        )
        
        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=0,
            pheromones_written=1,
            output_files=[self.SIM_DATA_FILENAME],
            extra_data={
                "sim_data_path": str(sim_data_path),
                "num_points": len(series),
                "pheromone_id": pheromone.id,
            },
        )
    
    def _load_simulation_params(self) -> dict:
        """
        Lädt die Simulations-Parameter aus dem experiment_profile.yaml
        (falls vorhanden), sonst Defaults.
        
        Hinweis: Das experiment_profile.yaml liegt im 00_System/-Verzeichnis
        des Workspaces, nicht im work_dir. Wir lesen es aus dem Workspace.
        """
        # Defaults (physikalisch plausible Werte)
        params = {
            "fluorescence_duration_s": 60.0,
            "measurement_interval_ms": 500,
            "target_temperature_c": 37.0,
            "ph_start": 7.4,
            "delta_ph": 2.0,
            "k_ph": 0.05,
            "pka": 6.4,
            "fluor_conc_um": 10.0,
        }
        
        profile_path = self.workspace_path / "00_System" / self.EXPERIMENT_PROFILE_FILENAME
        if not profile_path.exists():
            self.logger.info(
                "[%s] No experiment_profile.yaml found - using default parameters",
                self.caste_name.value,
            )
            return params
        
        try:
            raw_text = profile_path.read_text(encoding="utf-8")
            profile = yaml.safe_load(raw_text)
            if not isinstance(profile, dict):
                return params
            
            # Extrahiere die relevanten Parameter aus dem Profil
            profile_params = profile.get("parameters", {})
            
            if "fluorescence_duration_s" in profile_params:
                params["fluorescence_duration_s"] = float(profile_params["fluorescence_duration_s"])
            if "measurement_interval_ms" in profile_params:
                params["measurement_interval_ms"] = int(profile_params["measurement_interval_ms"])
            if "target_temperature_c" in profile_params:
                params["target_temperature_c"] = float(profile_params["target_temperature_c"])
            # Fluorescein-Konzentration aus dem Profil (in mM, umrechnen in µM)
            if "fluorescein_concentration_mm" in profile_params:
                params["fluor_conc_um"] = float(profile_params["fluorescein_concentration_mm"]) * 1000.0
            
        except (yaml.YAMLError, ValueError, TypeError) as exc:
            self.logger.warning(
                "[%s] Failed to parse experiment_profile.yaml: %s - using defaults",
                self.caste_name.value,
                exc,
            )
        
        return params
    
    def _write_sim_data(self, sim_data_path: Path, series: list[dict]) -> None:
        """Schreibt die simulierte Zeitreihe als CSV (atomar)."""
        sim_data_path.parent.mkdir(parents=True, exist_ok=True)
        
        temp_path = sim_data_path.with_suffix(".csv.tmp")
        with temp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["time_ms", "temp_c", "ph", "fluorescence_au"],
            )
            writer.writeheader()
            writer.writerows(series)
        temp_path.replace(sim_data_path)
        
        self.logger.info("[%s] Wrote sim_data.csv (%d points) to %s",
                        self.caste_name.value, len(series), sim_data_path)
    
    def _build_simulation_summary(self, series: list[dict]) -> str:
        """Erzeugt eine kurze Zusammenfassung der Simulation für das Pheromon."""
        if not series:
            return "Empty simulation"
        
        first = series[0]
        last = series[-1]
        
        return (
            f"Simulation: {len(series)} points, "
            f"temp {first['temp_c']}°C → {last['temp_c']}°C, "
            f"pH {first['ph']} → {last['ph']}, "
            f"fluorescence {first['fluorescence_au']} → {last['fluorescence_au']} a.u."
        )

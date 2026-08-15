"""
src/castes/executor.py
Die ExecutorCaste — die Brücke zwischen Myrmex und der Hardware.

Der Executor liest das experiment_profile.yaml (vom Planner erstellt),
validiert es gegen das Hardware-Profil, und schreibt ein experiment.json
in die Hardware-Queue.

Der Executor ist rein deterministisch — kein LLM. Er ist eine reine
Konvertierungs- und Validierungs-Kaste.

Erweitert um Warten auf Hardware-Ergebnisse (Prompt 18b).
"""
from __future__ import annotations
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.castes.hardware_profile import HardwareProfile, load_hardware_profile, find_active_profile
from src.castes.hardware_profile import ReagentsConfig
from src.castes.reagent_converter import convert_concentrations_to_reagents
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType

logger = logging.getLogger("caste.executor")


class HardwareValidationException(Exception):
    """
    Wird geworfen, wenn das experiment_profile.yaml die Hardware-Limits
    oder Reagenzien-Spezifikationen verletzt.
    """
    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


class ExecutorCaste(BaseCaste):
    """
    Die ExecutorCaste — validiert und übergibt Experimente an die Hardware.
    """
    
    caste_name = CasteName.EXECUTOR
    role = "Experimente an die Hardware übergeben"
    specialization = "Profil-Validierung und Format-Konvertierung"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]
    
    EXPERIMENT_PROFILE_FILENAME = "experiment_profile.yaml"
    EXPERIMENT_JSON_FILENAME = "experiment.json"
    
    # Timeout für das Warten auf Hardware-Ergebnisse
    HARDWARE_WAIT_TIMEOUT_S = 300  # 5 Minuten
    HARDWARE_POLL_INTERVAL_S = 1.0  # 1 Sekunde
    
    def __init__(
        self,
        workspace_path: Path | None = None,
        hardware_profile: HardwareProfile | None = None,
    ):
        super().__init__(workspace_path=workspace_path)
        self._hardware_profile = hardware_profile
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Ausführung aus:
        1. Lädt das Hardware-Profil
        2. Lädt das experiment_profile.yaml
        3. Konvertiert Konzentrationen → Reagenzien
        4. Validiert die GENERIERTEN Reagenzien gegen das Hardware-Profil
        5. Schreibt experiment.json in die Hardware-Queue
        6. Wartet auf die Hardware-Ergebnisse
        7. Schreibt ein TRAIL-Pheromon mit der Bestätigung
        
        WICHTIG: Die Reagenzien-Validierung muss NACH der Umrechnung stattfinden,
        da das experiment_profile.yaml nur Konzentrationen enthält, keine Reagenzien.
        """
        self.logger.info("[%s] Starting execution", self.caste_name.value)
        
        # 1. Hardware-Profil laden
        profile = self._get_hardware_profile()
        if profile is None:
            self.logger.warning(
                "[%s] Kein Hardware-Profil gefunden - verwende minimale Konfiguration",
                self.caste_name.value,
            )
            # Verwende minimales Profil als Fallback
            profile = HardwareProfile(
                metadata={"name": "Minimal Profile", "version": "1.0.0"},
                limits={},
                reagents=ReagentsConfig(),
                defaults={},
            )
        
        # 2. experiment_profile.yaml laden
        experiment_profile = self._load_experiment_profile()
        if experiment_profile is None:
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=False,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                error_message="Kein experiment_profile.yaml gefunden",
            )
        
        # 3. Konzentrationen → Reagenzien umrechnen (BEVOR die Validierung!)
        parameters = experiment_profile.get("parameters", {})
        reagents = convert_concentrations_to_reagents(parameters)
        
        self.logger.info(
            "[%s] Generated %d reagents from concentrations",
            self.caste_name.value, len(reagents),
        )
        
        # 4. Validieren (Parameter-Limits + generierte Reagenzien)
        violations = self._validate_against_profile_with_reagents(
            experiment_profile, profile, reagents
        )
        if violations:
            self.logger.error("[%s] Validation failed: %s", self.caste_name.value, violations)
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=False,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                error_message=f"Validierung fehlgeschlagen: {'; '.join(violations)}",
                extra_data={"violations": violations},
            )
        
        # 5. experiment.json schreiben (mit bereits validierten Reagenzien)
        job_payload = self._build_job_payload_with_reagents(experiment_profile, profile, reagents)
        queue_path = self._write_experiment_json(job_payload)
        
        # 6. Warte auf Hardware-Ergebnisse
        hardware_results = self._wait_for_hardware_results(work_dir)
        
        if hardware_results is None:
            # Timeout oder Fehler
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=False,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                error_message="Hardware did not produce results within timeout",
                extra_data={"timeout_s": self.HARDWARE_WAIT_TIMEOUT_S},
            )
        
        # 7. TRAIL-Pheromon schreiben
        measurement_csv_path = hardware_results.get("measurement_csv_path")
        hardware_protocol_path = hardware_results.get("hardware_protocol_path")
        
        summary = f"Hardware execution completed for {work_dir.name}"
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=summary,
            tags=["execution", "hardware"],
            strength=0.5,
            relevance=0.6,
        )
        
        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=0,
            pheromones_written=1,
            output_files=[
                str(queue_path),
                str(measurement_csv_path) if measurement_csv_path else "",
                str(hardware_protocol_path) if hardware_protocol_path else "",
            ],
            extra_data={
                "job_id": job_payload["job_id"],
                "queue_path": str(queue_path),
                "pheromone_id": pheromone.id,
                "measurement_csv_path": str(measurement_csv_path) if measurement_csv_path else None,
                "hardware_protocol_path": str(hardware_protocol_path) if hardware_protocol_path else None,
            },
        )
    
    def _wait_for_hardware_results(self, work_dir: Path) -> dict | None:
        """
        Wartet auf die Hardware-Ergebnisse.
        
        Args:
            work_dir: Das Arbeitsverzeichnis (z.B. Cycle_001).
        
        Returns:
            Ein dict mit den Pfaden zu den Ergebnissen, oder None bei Timeout.
        """
        hardware_dir = work_dir / "B_Hardware"
        measurement_csv_path = hardware_dir / "measurement.csv"
        hardware_protocol_path = hardware_dir / "hardware_protocol.json"
        
        start_time = time.monotonic()
        
        while True:
            # Prüfe ob beide Dateien existieren
            if measurement_csv_path.exists() and hardware_protocol_path.exists():
                self.logger.info(
                    "[%s] Hardware results received: %s, %s",
                    self.caste_name.value,
                    measurement_csv_path,
                    hardware_protocol_path,
                )
                return {
                    "measurement_csv_path": measurement_csv_path,
                    "hardware_protocol_path": hardware_protocol_path,
                }
            
            # Prüfe Timeout
            elapsed = time.monotonic() - start_time
            if elapsed >= self.HARDWARE_WAIT_TIMEOUT_S:
                self.logger.error(
                    "[%s] Timeout waiting for hardware results (%.1fs)",
                    self.caste_name.value,
                    elapsed,
                )
                return None
            
            time.sleep(self.HARDWARE_POLL_INTERVAL_S)

    def _wait_for_hardware_results_fast(self, work_dir: Path) -> dict | None:
        """
        Wartet auf die Hardware-Ergebnisse (schnelle Version für Tests).
        Prüft nur einmal ohne Warten.
        
        Args:
            work_dir: Das Arbeitsverzeichnis (z.B. Cycle_001).
        
        Returns:
            Ein dict mit den Pfaden zu den Ergebnissen, oder None wenn nicht vorhanden.
        """
        hardware_dir = work_dir / "B_Hardware"
        measurement_csv_path = hardware_dir / "measurement.csv"
        hardware_protocol_path = hardware_dir / "hardware_protocol.json"
        
        if measurement_csv_path.exists() and hardware_protocol_path.exists():
            self.logger.info(
                "[%s] Hardware results received: %s, %s",
                self.caste_name.value,
                measurement_csv_path,
                hardware_protocol_path,
            )
            return {
                "measurement_csv_path": measurement_csv_path,
                "hardware_protocol_path": hardware_protocol_path,
            }
        
        return None
    
    def _get_hardware_profile(self) -> HardwareProfile | None:
        """Lädt das Hardware-Profil."""
        if self._hardware_profile is not None:
            return self._hardware_profile
        
        profiles_dir = self.workspace_path / "hardware_profiles"
        profile_path = find_active_profile(profiles_dir)
        
        if profile_path is None:
            self.logger.warning("[%s] Kein Hardware-Profil in %s", self.caste_name.value, profiles_dir)
            return None
        
        try:
            return load_hardware_profile(profile_path)
        except Exception as e:
            self.logger.error("[%s] Fehler beim Laden des Profils: %s", self.caste_name.value, e)
            return None

    def _load_hardware_profile(self) -> dict | None:
        """
        Lädt das Hardware-Profil aus dem hardware_profiles/-Verzeichnis.
        
        Returns:
            Ein dict mit dem Hardware-Profil, oder None wenn nicht gefunden.
        """
        hardware_profiles_dir = self.workspace_path / "hardware_profiles"
        
        if not hardware_profiles_dir.exists():
            self.logger.warning(
                "[%s] Kein Hardware-Profil in %s",
                self.caste_name.value, hardware_profiles_dir,
            )
            return None
        
        # Finde das erste YAML-Profil im Verzeichnis
        profile_files = list(hardware_profiles_dir.glob("*.yaml")) + list(hardware_profiles_dir.glob("*.yml"))
        
        if not profile_files:
            self.logger.warning(
                "[%s] Keine Hardware-Profil-Dateien in %s gefunden",
                self.caste_name.value, hardware_profiles_dir,
            )
            return None
        
        # Lade das erste Profil
        profile_path = profile_files[0]
        try:
            raw_text = profile_path.read_text(encoding="utf-8")
            import yaml
            profile = yaml.safe_load(raw_text)
            
            if not isinstance(profile, dict):
                self.logger.warning(
                    "[%s] Hardware-Profil %s ist kein gültiges YAML",
                    self.caste_name.value, profile_path,
                )
                return None
            
            self.logger.info(
                "[%s] Hardware-Profil geladen: %s",
                self.caste_name.value, profile_path,
            )
            return profile
            
        except (yaml.YAMLError, ValueError, TypeError) as e:
            self.logger.error(
                "[%s] Fehler beim Laden des Hardware-Profils %s: %s",
                self.caste_name.value, profile_path, e,
            )
            return None
    
    def _load_experiment_profile(self) -> dict | None:
        """Lädt das experiment_profile.yaml."""
        import yaml
        
        profile_path = self.workspace_path / "00_System" / self.EXPERIMENT_PROFILE_FILENAME
        if not profile_path.exists():
            self.logger.warning("[%s] Kein experiment_profile.yaml", self.caste_name.value)
            return None
        
        try:
            raw_text = profile_path.read_text(encoding="utf-8")
            return yaml.safe_load(raw_text)
        except Exception as e:
            self.logger.error("[%s] Fehler beim Laden: %s", self.caste_name.value, e)
            return None
    
    def _validate_against_profile_with_reagents(
        self,
        experiment_profile: dict,
        hardware_profile: HardwareProfile,
        reagents: list[dict],
    ) -> list[str]:
        """
        Validiert das experiment_profile.yaml gegen das Hardware-Profil.
        
        WICHTIG: Diese Methode erwartet die GENERIERTEN Reagenzien als Parameter.
        Die Umrechnung von Konzentrationen → Reagenzien muss VOR dem Aufruf
        dieser Methode stattfinden.
        
        Args:
            experiment_profile: Das geladene experiment_profile.yaml.
            hardware_profile: Das Hardware-Profil mit Limits und erwarteten Reagenzien.
            reagents: Die bereits generierten Reagenzien (mit volume_ul und concentration_mm).
        
        Returns:
            Eine Liste von Verletzungen (leer = alles OK).
        """
        violations: list[str] = []
        
        # 1. Parameter gegen Limits prüfen
        parameters = experiment_profile.get("parameters", {})
        for param_name, limit in hardware_profile.limits.items():
            value = parameters.get(param_name)
            if value is None:
                continue
            if limit.min is not None and value < limit.min:
                violations.append(f"{param_name}={value} unter Minimum {limit.min}")
            if limit.max is not None and value > limit.max:
                violations.append(f"{param_name}={value} über Maximum {limit.max}")
        
        # 2. Reagenzien prüfen (die GENERIERTEN Reagenzien, nicht das rohe Profil!)
        expected_names = {r.name for r in hardware_profile.reagents.expected}
        actual_names = {r.get("reagent_name", "") for r in reagents}
        
        # Prüfe jedes generierte Reagenz
        for reagent in reagents:
            name = reagent.get("reagent_name", "")
            
            # Finde die Spezifikation für dieses Reagenz
            spec = next((r for r in hardware_profile.reagents.expected if r.name == name), None)
            if spec is None:
                continue
            
            # Konzentration prüfen
            conc = reagent.get("concentration_mm", 0)
            if len(spec.concentration_range_mm) == 2:
                if conc < spec.concentration_range_mm[0] or conc > spec.concentration_range_mm[1]:
                    violations.append(
                        f"Reagenz {name}: Konzentration {conc} außerhalb "
                        f"[{spec.concentration_range_mm[0]}, {spec.concentration_range_mm[1]}]"
                    )
            
            # Volumen prüfen
            vol = reagent.get("volume_ul", 0)
            if len(spec.volume_range_ul) == 2:
                if vol < spec.volume_range_ul[0] or vol > spec.volume_range_ul[1]:
                    violations.append(
                        f"Reagenz {name}: Volumen {vol} außerhalb "
                        f"[{spec.volume_range_ul[0]}, {spec.volume_range_ul[1]}]"
                    )
        
        # Fehlende Reagenzien prüfen
        missing = expected_names - actual_names
        if missing:
            violations.append(f"Fehlende Reagenzien: {', '.join(missing)}")
        
        # Gesamt-Volumen prüfen
        if hardware_profile.reagents.total_volume_max_ul is not None:
            total_vol = sum(r.get("volume_ul", 0) for r in reagents)
            if total_vol > hardware_profile.reagents.total_volume_max_ul:
                violations.append(
                    f"Gesamt-Volumen {total_vol} über Maximum "
                    f"{hardware_profile.reagents.total_volume_max_ul}"
                )
        
        return violations
    
    def _build_job_payload_with_reagents(
        self,
        experiment_profile: dict,
        hardware_profile: HardwareProfile,
        reagents: list[dict],
    ) -> dict:
        """
        Baut den experiment.json-Payload aus dem experiment_profile.yaml.
        
        WICHTIG: Diese Methode erwartet die bereits generierten Reagenzien als Parameter.
        
        Args:
            experiment_profile: Das geladene experiment_profile.yaml.
            hardware_profile: Das Hardware-Profil mit Defaults.
            reagents: Die bereits generierten Reagenzien.
        
        Returns:
            Den fertigen Payload für die experiment.json.
        """
        parameters = dict(experiment_profile.get("parameters", {}))
        
        # Defaults anwenden
        for key, value in hardware_profile.defaults.items():
            if key not in parameters:
                parameters[key] = value
        
        # Reagenzien einfügen (bereits generiert und validiert)
        parameters["reagents"] = reagents
        
        # station_4_action aus Defaults
        station_4_action = hardware_profile.defaults.get("station_4_action", "FLUORESCENCE")
        
        # Job-ID generieren
        job_id = f"myrmex_{uuid.uuid4().hex[:8]}"
        
        return {
            "job_id": job_id,
            "cycle_id": experiment_profile.get("cycle_id", "unknown"),
            "parameters": parameters,
            "station_4_action": station_4_action,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _validate_against_profile(
        self,
        experiment_profile: dict,
        hardware_profile: HardwareProfile,
    ) -> list[str]:
        """
        DEPRECATED: Diese Methode wird nicht mehr verwendet.
        Bitte _validate_against_profile_with_reagents() verwenden.
        
        Validiert das experiment_profile.yaml gegen das Hardware-Profil.
        Gibt eine Liste von Verletzungen zurück (leer = alles OK).
        """
        # Alte Logik für Abwärtskompatibilität
        violations: list[str] = []
        
        # 1. Parameter gegen Limits prüfen
        parameters = experiment_profile.get("parameters", {})
        for param_name, limit in hardware_profile.limits.items():
            value = parameters.get(param_name)
            if value is None:
                continue
            if limit.min is not None and value < limit.min:
                violations.append(f"{param_name}={value} unter Minimum {limit.min}")
            if limit.max is not None and value > limit.max:
                violations.append(f"{param_name}={value} über Maximum {limit.max}")
        
        # 2. Reagenzien prüfen (aus dem Profil - wird nicht mehr verwendet)
        reagents = parameters.get("reagents", [])
        expected_names = {r.name for r in hardware_profile.reagents.expected}
        actual_names = set()
        
        for reagent in reagents:
            name = reagent.get("reagent_name", "")
            actual_names.add(name)
            
            # Konzentration prüfen
            spec = next((r for r in hardware_profile.reagents.expected if r.name == name), None)
            if spec is not None and len(spec.concentration_range_mm) == 2:
                conc = reagent.get("concentration_mm", 0)
                if conc < spec.concentration_range_mm[0] or conc > spec.concentration_range_mm[1]:
                    violations.append(
                        f"Reagenz {name}: Konzentration {conc} außerhalb "
                        f"[{spec.concentration_range_mm[0]}, {spec.concentration_range_mm[1]}]"
                    )
            
            # Volumen prüfen
            if spec is not None and len(spec.volume_range_ul) == 2:
                vol = reagent.get("volume_ul", 0)
                if vol < spec.volume_range_ul[0] or vol > spec.volume_range_ul[1]:
                    violations.append(
                        f"Reagenz {name}: Volumen {vol} außerhalb "
                        f"[{spec.volume_range_ul[0]}, {spec.volume_range_ul[1]}]"
                    )
        
        # Fehlende Reagenzien
        missing = expected_names - actual_names
        if missing:
            violations.append(f"Fehlende Reagenzien: {', '.join(missing)}")
        
        # Gesamt-Volumen prüfen
        if hardware_profile.reagents.total_volume_max_ul is not None:
            total_vol = sum(r.get("volume_ul", 0) for r in reagents)
            if total_vol > hardware_profile.reagents.total_volume_max_ul:
                violations.append(
                    f"Gesamt-Volumen {total_vol} über Maximum "
                    f"{hardware_profile.reagents.total_volume_max_ul}"
                )
        
        return violations
    
    def _build_job_payload(
        self,
        experiment_profile: dict,
        hardware_profile: HardwareProfile,
    ) -> dict:
        """
        DEPRECATED: Diese Methode wird nicht mehr verwendet.
        Bitte _build_job_payload_with_reagents() verwenden.
        
        Baut den experiment.json-Payload aus dem experiment_profile.yaml.
        Wendet dabei die Defaults aus dem Hardware-Profil an und rechnet
        Konzentrationen in Reagenzien-Volumina um.
        """
        # Alte Logik für Abwärtskompatibilität
        parameters = dict(experiment_profile.get("parameters", {}))
        
        # Defaults anwenden
        for key, value in hardware_profile.defaults.items():
            if key not in parameters:
                parameters[key] = value
        
        # WICHTIG: Konzentrationen → Reagenzien umrechnen
        # Der Planner speichert Konzentrationen (z.B. fecl3_concentration_mm),
        # aber die Hardware erwartet Reagenzien mit Volumina.
        reagents = convert_concentrations_to_reagents(parameters)
        parameters["reagents"] = reagents
        
        # station_4_action aus Defaults
        station_4_action = hardware_profile.defaults.get("station_4_action", "FLUORESCENCE")
        
        # Job-ID generieren
        job_id = f"myrmex_{uuid.uuid4().hex[:8]}"
        
        return {
            "job_id": job_id,
            "cycle_id": experiment_profile.get("cycle_id", "unknown"),
            "parameters": parameters,
            "station_4_action": station_4_action,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _write_experiment_json(self, job_payload: dict) -> Path:
        """Schreibt experiment.json atomar in die Hardware-Queue."""
        queue_dir = self.workspace_path / "03_Hardware_Queue"
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        queue_path = queue_dir / self.EXPERIMENT_JSON_FILENAME
        
        # Atomares Schreiben
        temp_path = queue_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(job_payload, indent=2), encoding="utf-8")
        temp_path.replace(queue_path)
        
        self.logger.info("[%s] Wrote experiment.json to %s", self.caste_name.value, queue_path)
        return queue_path

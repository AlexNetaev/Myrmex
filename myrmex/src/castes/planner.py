"""
src/castes/planner.py
Die PlannerCaste — plant das nächste Experiment mit OFAT-Strategie.

Diese Kaste arbeitet rein deterministisch — kein LLM, keine komplexe
Optimierung. Sie liest das aktuelle experiment_profile.yaml, führt den
nächsten OFAT-Schritt aus, und schreibt ein neues Profil sowie ein
TRAIL-Pheromon mit dem Plan.

Kasten-Definition:
- caste_name: CasteName.PLANNER
- role: "Das nächste Experiment planen"
- specialization: "OFAT-basierte Parameter-Exploration"
- reads_pheromones: [PheromoneType.TRAIL]  # liest Analyse-Ergebnisse vom Analyst
- writes_pheromones: [PheromoneType.TRAIL]  # schreibt den Plan als TRAIL
"""
from __future__ import annotations
from pathlib import Path
import yaml

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.castes.ofat import create_baseline_profile, next_ofat_step, get_current_parameter_name
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


class PlannerCaste(BaseCaste):
    """
    Die PlannerCaste — plant das nächste Experiment mit OFAT-Strategie.
    """
    
    caste_name = CasteName.PLANNER
    role = "Das nächste Experiment planen"
    specialization = "OFAT-basierte Parameter-Exploration"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]
    
    EXPERIMENT_PROFILE_FILENAME = "experiment_profile.yaml"
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Planung aus:
        1. Liest das aktuelle experiment_profile.yaml aus 00_System/
        2. Wenn kein Profil existiert → erstellt ein Basis-Profil
        3. Wenn Profil existiert → führt den nächsten OFAT-Schritt aus
        4. Schreibt das neue Profil zurück
        5. Schreibt ein TRAIL-Pheromon mit dem Plan
        """
        self.logger.info("[%s] Starting planning in %s", self.caste_name.value, work_dir)
        
        # 1. Aktuelles Profil lesen
        profile_path = self.workspace_path / "00_System" / self.EXPERIMENT_PROFILE_FILENAME
        current_profile = self._load_profile(profile_path)
        
        # 2. OFAT-Schritt ausführen
        if current_profile is None:
            # Kein Profil → Basis-Profil erstellen
            new_profile = create_baseline_profile()
            plan_description = "Created baseline profile with default parameters"
        else:
            # Profil existiert → nächsten OFAT-Schritt
            new_profile = next_ofat_step(current_profile)
            current_param = get_current_parameter_name(current_profile)
            new_param = get_current_parameter_name(new_profile)
            new_value = new_profile["parameters"].get(new_param, "?")
            plan_description = f"OFAT step: varied '{new_param}' to {new_value}"
        
        # 3. Neues Profil schreiben
        self._save_profile(profile_path, new_profile)
        
        # 4. TRAIL-Pheromon mit dem Plan schreiben
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=plan_description,
            tags=["planning", "ofat"],
            strength=0.5,
            relevance=0.6,
        )
        
        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=0,
            pheromones_written=1,
            output_files=[self.EXPERIMENT_PROFILE_FILENAME],
            extra_data={
                "plan_description": plan_description,
                "pheromone_id": pheromone.id,
                "ofat_iterations_completed": new_profile["ofat_state"].get("iterations_completed", 0),
            },
        )
    
    def _load_profile(self, profile_path: Path) -> dict | None:
        """Lädt das experiment_profile.yaml, oder gibt None zurück wenn es nicht existiert."""
        if not profile_path.exists():
            self.logger.info("[%s] No profile found at %s, will create baseline", 
                           self.caste_name.value, profile_path)
            return None
        
        try:
            text = profile_path.read_text(encoding="utf-8")
            profile = yaml.safe_load(text)
            if not isinstance(profile, dict):
                self.logger.warning("[%s] Profile at %s is not a dict, will create baseline",
                                  self.caste_name.value, profile_path)
                return None
            return profile
        except yaml.YAMLError as exc:
            self.logger.warning("[%s] Failed to parse profile at %s: %s, will create baseline",
                              self.caste_name.value, profile_path, exc)
            return None
    
    def _save_profile(self, profile_path: Path, profile: dict) -> None:
        """Schreibt das experiment_profile.yaml atomar."""
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomares Schreiben: erst in temp-Datei, dann umbenennen
        temp_path = profile_path.with_suffix(".yaml.tmp")
        temp_path.write_text(yaml.dump(profile, default_flow_style=False), encoding="utf-8")
        temp_path.replace(profile_path)
        
        self.logger.info("[%s] Wrote profile to %s", self.caste_name.value, profile_path)

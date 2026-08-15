"""
src/castes/planner.py
Die PlannerCaste — plant das nächste Experiment.

In dieser Version nutzt sie ein LLM für die strategische Planung.
Die bestehende OFAT-Logik bleibt als Fallback erhalten.

Kasten-Definition:
- caste_name: CasteName.PLANNER
- role: "Das nächste Experiment planen"
- specialization: "LLM-basierte Experiment-Planung mit deterministischem Fallback"
- reads_pheromones: [PheromoneType.TRAIL, PheromoneType.CRYSTAL]
- writes_pheromones: [PheromoneType.TRAIL]
"""
from __future__ import annotations
import logging
from pathlib import Path
import yaml

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType
from src.castes.plan_models import PlanModel, ExperimentStrategy

logger = logging.getLogger("caste.planner")

# LLM-Konfiguration (identisch zu den anderen Kasten)
OLLAMA_MODEL = "gemma4:31b-cloud"
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_CONTEXT_SIZE = 4096

# Liste der gültigen Parameter für die Fenton-Fluoreszenz-Experimente
VALID_PARAMETERS = [
    "ascorbic_acid_concentration_mm",
    "fecl3_concentration_mm",
    "h2o2_concentration_mm",
    "fluorescein_concentration_mm",
    "phosphate_buffer_concentration_mm",
    "target_temperature_c",
    "mixing_speed_rpm",
    "mixing_time_s",
    "heating_time_s",
    "measurement_interval_ms",
    "fluorescence_duration_s",
]

# Physikalische Grenzen für die Parameter
PARAMETER_BOUNDS = {
    "ascorbic_acid_concentration_mm": (0.1, 100.0),
    "fecl3_concentration_mm": (0.01, 10.0),
    "h2o2_concentration_mm": (1.0, 200.0),
    "fluorescein_concentration_mm": (0.001, 0.1),
    "phosphate_buffer_concentration_mm": (1.0, 200.0),
    "target_temperature_c": (20.0, 80.0),
    "mixing_speed_rpm": (100, 1500),
    "mixing_time_s": (1.0, 120.0),
    "heating_time_s": (5.0, 300.0),
    "measurement_interval_ms": (100, 5000),
    "fluorescence_duration_s": (10.0, 600.0),
}


class PlannerCaste(BaseCaste):
    """
    Die PlannerCaste — plant das nächste Experiment.
    
    In dieser Version nutzt sie ein LLM für die strategische Planung.
    Die bestehende OFAT-Logik bleibt als Fallback erhalten.
    """

    caste_name = CasteName.PLANNER
    role = "Das nächste Experiment planen"
    specialization = "LLM-basierte Experiment-Planung mit deterministischem Fallback"
    reads_pheromones = [PheromoneType.TRAIL, PheromoneType.CRYSTAL]
    writes_pheromones = [PheromoneType.TRAIL]

    EXPERIMENT_PROFILE_FILENAME = "experiment_profile.yaml"

    # Tags, die als Hypothesen erkannt werden
    HYPOTHESIS_TAGS = {"hypothesis", "experiment_iteration"}

    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Experiment-Planung aus:
        1. Liest das aktuelle experiment_profile.yaml.
        2. Liest Hypothesen-Pheromone und Theorie-Baseline.
        3. Versucht die LLM-basierte Planung.
        4. Falls LLM fehlschlägt: Verwendet OFAT-Fallback.
        5. Schreibt das neue experiment_profile.yaml.
        6. Schreibt ein TRAIL-Pheromon mit dem Plan.
        """
        self.logger.info("[%s] Starting experiment planning", self.caste_name.value)

        # 1. Aktuelles Profil laden
        current_profile = self._load_current_profile()

        # 2. Hypothesen und Theorie-Kontext sammeln
        hypotheses = self._collect_hypotheses()
        theory_context = self._read_theory_baseline()

        # 3. LLM-basierte Planung versuchen
        plan = None
        llm_used = False
        try:
            plan = self._plan_with_llm(current_profile, hypotheses, theory_context)
            llm_used = True
            self.logger.info("[%s] LLM-based planning completed successfully", self.caste_name.value)
        except Exception as e:
            self.logger.warning(
                "[%s] LLM-based planning failed: %s. Falling back to OFAT logic.",
                self.caste_name.value, e,
            )

        # 4. Fallback: OFAT-Logik
        if plan is None:
            plan = self._plan_with_ofat(current_profile)
            llm_used = False

        # 5. Parameter-Grenzen prüfen und ggf. anpassen
        plan = self._validate_plan_against_bounds(plan)

        # 6. Neues experiment_profile.yaml schreiben
        new_profile = self._apply_plan_to_profile(current_profile, plan)
        self._write_experiment_profile(new_profile)

        # 7. TRAIL-Pheromon mit dem Plan schreiben
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=plan["summary"],
            tags=["plan", "experiment", plan["strategy"]],
            strength=0.5,
            relevance=0.7,
        )

        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=len(hypotheses),
            pheromones_written=1,
            output_files=[self.EXPERIMENT_PROFILE_FILENAME],
            extra_data={
                "llm_used": llm_used,
                "confidence": plan.get("confidence", "unknown"),
                "strategy": plan["strategy"],
                "parameter_changed": plan["parameter_to_change"],
                "new_value": plan["new_value"],
                "pheromone_id": pheromone.id,
            },
        )

    def _plan_with_llm(
        self,
        current_profile: dict,
        hypotheses: list,
        theory_context: str,
    ) -> dict:
        """
        Führt die LLM-basierte Planung durch.
        """
        # Aktuelles Profil formatieren
        params = current_profile.get("parameters", {})
        params_text = "\n".join(f"  {k}: {v}" for k, v in params.items())

        # Hypothesen formatieren
        hypotheses_text = ""
        if hypotheses:
            for h in hypotheses[:3]:  # Max 3 Hypothesen
                hypotheses_text += f"- [{h.source_agent}] ({', '.join(h.tags)}): {h.content}\n"
        else:
            hypotheses_text = "(no hypotheses available)"

        prompt = f"""You are the Experiment Planner for an autonomous self-driving laboratory
studying the Fenton reaction with fluorescein as a pH-sensitive fluorophore.

## Current Experiment Profile
{params_text}

## Recent Hypotheses (from HypothesizerCaste)
{hypotheses_text}

## Current Theory Baseline
{theory_context[:2000]}

## Available Parameters to Adjust
{', '.join(VALID_PARAMETERS)}

## Your Task
Plan the next experiment by:
1. Choosing a strategy: 'ofat', 'doe', 'exploration', 'replication', or 'exploitation'
2. Selecting ONE parameter to change (from the list above)
3. Proposing a new value (physically plausible, within these bounds):
   - ascorbic_acid_concentration_mm: 0.1-100 mM
   - fecl3_concentration_mm: 0.01-10 mM
   - h2o2_concentration_mm: 1-200 mM
   - fluorescein_concentration_mm: 0.001-0.1 mM
   - phosphate_buffer_concentration_mm: 1-200 mM
   - target_temperature_c: 20-80°C
   - mixing_speed_rpm: 100-1500
   - mixing_time_s: 1-120 s
   - heating_time_s: 5-300 s
   - measurement_interval_ms: 100-5000 ms
   - fluorescence_duration_s: 10-600 s
4. Explaining WHY you chose this parameter and value
5. Stating what you EXPECT to observe
6. Assessing your confidence ('high', 'medium', 'low')
7. Writing a short summary (max 200 characters)

Be specific, quantitative, and scientifically rigorous. If a hypothesis suggests
a specific parameter change, strongly consider following it. Otherwise, use
scientific judgment to decide the most informative next step.
"""

        system_prompt = (
            "You are the Experiment Planner for an autonomous self-driving laboratory "
            "specializing in Fenton reaction kinetics. You plan scientifically rigorous "
            "experiments based on hypotheses, current data, and theoretical knowledge. "
            "Your plans must be specific, testable, and physically plausible."
        )

        # LLM aufrufen
        result = self.ask_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            response_model=PlanModel,
            max_retries=DEFAULT_MAX_RETRIES,
            temperature=DEFAULT_TEMPERATURE,
            context_size=DEFAULT_CONTEXT_SIZE,
        )

        # In dict umwandeln
        return {
            "strategy": result.strategy.value,
            "parameter_to_change": result.parameter_to_change,
            "new_value": result.new_value,
            "reasoning": result.reasoning,
            "expected_outcome": result.expected_outcome,
            "confidence": result.confidence,
            "summary": result.summary,
        }

    def _plan_with_ofat(self, current_profile: dict) -> dict:
        """
        Deterministischer Fallback: OFAT-Logik (One-Factor-at-a-Time).
        Dies ist die bestehende Logik aus src/castes/ofat.py.
        """
        from src.castes.ofat import next_ofat_step, get_current_parameter_name

        # OFAT-Schritt berechnen
        new_profile = next_ofat_step(current_profile)
        params = new_profile.get("parameters", {})
        old_params = current_profile.get("parameters", {})

        # Finde den Parameter, der sich geändert hat
        changed_param = None
        new_value = None
        for key in params:
            if params[key] != old_params.get(key):
                changed_param = key
                new_value = params[key]
                break

        if changed_param is None:
            # Fallback: ersten Parameter leicht ändern
            changed_param = "target_temperature_c"
            new_value = old_params.get("target_temperature_c", 37.0) + 1.0

        param_name = get_current_parameter_name(current_profile)

        return {
            "strategy": ExperimentStrategy.OFAT.value,
            "parameter_to_change": changed_param,
            "new_value": new_value,
            "reasoning": (
                f"OFAT step: systematically varying {param_name} to map "
                f"the response surface."
            ),
            "expected_outcome": (
                f"Observe the effect of {changed_param} on fluorescence kinetics."
            ),
            "confidence": "medium",
            "summary": f"OFAT: {changed_param} -> {new_value}",
        }

    def _validate_plan_against_bounds(self, plan: dict) -> dict:
        """
        Prüft den Plan gegen die physikalischen Grenzen und passt ggf. an.
        """
        param = plan.get("parameter_to_change")
        value = plan.get("new_value")

        if param not in PARAMETER_BOUNDS:
            self.logger.warning(
                "[%s] Unknown parameter '%s' - falling back to target_temperature_c",
                self.caste_name.value, param,
            )
            plan["parameter_to_change"] = "target_temperature_c"
            plan["new_value"] = 37.0
            return plan

        min_val, max_val = PARAMETER_BOUNDS[param]
        if value < min_val or value > max_val:
            self.logger.warning(
                "[%s] Value %.3f for %s is out of bounds [%.3f, %.3f] - clamping",
                self.caste_name.value, value, param, min_val, max_val,
            )
            plan["new_value"] = max(min_val, min(max_val, value))

        return plan

    def _apply_plan_to_profile(self, current_profile: dict, plan: dict) -> dict:
        """
        Wendet den Plan auf das Profil an: Ändert den gewählten Parameter
        auf den neuen Wert.
        """
        import copy
        new_profile = copy.deepcopy(current_profile)

        if "parameters" not in new_profile:
            new_profile["parameters"] = {}

        param = plan["parameter_to_change"]
        new_value = plan["new_value"]

        new_profile["parameters"][param] = new_value

        # Zyklus-ID hochzählen
        if "cycle_id" in new_profile:
            current_cycle = new_profile.get("cycle_id", "Cycle_000")
            try:
                num = int(current_cycle.split("_")[1])
                new_profile["cycle_id"] = f"Cycle_{num + 1:03d}"
            except (IndexError, ValueError):
                pass

        return new_profile

    def _load_current_profile(self) -> dict:
        """Lädt das aktuelle experiment_profile.yaml."""
        profile_path = self.workspace_path / "00_System" / self.EXPERIMENT_PROFILE_FILENAME

        if not profile_path.exists():
            self.logger.info(
                "[%s] No experiment_profile.yaml found - using baseline profile",
                self.caste_name.value,
            )
            from src.castes.ofat import create_baseline_profile
            return create_baseline_profile()

        try:
            raw_text = profile_path.read_text(encoding="utf-8")
            profile = yaml.safe_load(raw_text)
            if isinstance(profile, dict):
                return profile
        except (yaml.YAMLError, ValueError, TypeError) as e:
            self.logger.warning(
                "[%s] Failed to parse experiment_profile.yaml: %s - using baseline",
                self.caste_name.value, e,
            )

        from src.castes.ofat import create_baseline_profile
        return create_baseline_profile()

    def _write_experiment_profile(self, profile: dict) -> None:
        """Schreibt das neue experiment_profile.yaml (atomar)."""
        profile_path = self.workspace_path / "00_System" / self.EXPERIMENT_PROFILE_FILENAME
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = profile_path.with_suffix(".yaml.tmp")
        temp_path.write_text(yaml.dump(profile, default_flow_style=False), encoding="utf-8")
        temp_path.replace(profile_path)

        self.logger.info("[%s] Wrote experiment_profile.yaml to %s", self.caste_name.value, profile_path)

    def _collect_hypotheses(self) -> list:
        """Sammelt Hypothesen-Pheromone aus dem Feld."""
        all_trails = self.read_pheromones(pheromone_type=PheromoneType.TRAIL)
        return [p for p in all_trails if any(tag in self.HYPOTHESIS_TAGS for tag in p.tags)]

    def _read_theory_baseline(self) -> str:
        """Liest die theory_baseline.md für den Kontext."""
        theory_path = self.workspace_path / "04_Knowledge_Base" / "theory_baseline.md"
        if not theory_path.exists():
            return ""
        try:
            return theory_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.warning("[%s] Could not read theory_baseline.md: %s", self.caste_name.value, e)
            return ""

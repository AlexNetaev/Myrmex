"""
src/loops/loop_runner.py
Der Loop-Runner — orchestriert die 4 Schleifen basierend auf dem Arbiter-Plan.
"""
from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# config.py ist im Projekt-Root, nicht in src/
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
import config

from src.models.loop import (
    LoopName, LoopState, LoopStatus, ActionType,
    LoopExecutionResult, LoopCycleResult
)
from src.models.arbiter import ArbiterPlan
from src.pheromones.pheromone_field import PheromoneField, EvaporationResult
from src.loops.loop_definitions import get_loop_definition

logger = logging.getLogger(__name__)


class LoopRunner:
    """
    Der Loop-Runner — orchestriert die 4 Schleifen basierend auf dem Arbiter-Plan.
    
    In Phase 1 sind die Schleifen-Ausführungen Platzhalter. Die tatsächlichen
    Kasten-Logiken (Hypothesizer, Simulator, Analyst, etc.) werden in Phase 2+
    implementiert.
    """
    
    # Energie-Änderungen pro Aktionstyp
    ENERGY_CHANGES = {
        ActionType.MEASURE: +20.0,
        ActionType.SIMULATE: -5.0,
        ActionType.ANALYZE: -10.0,
        ActionType.CONSOLIDATE: -5.0,
    }
    
    # Aktionstyp pro Schleife (Platzhalter-Logik)
    LOOP_ACTION_MAP = {
        LoopName.LOOP_A_SIMULATION: ActionType.SIMULATE,
        LoopName.LOOP_B_EXPERIMENT: ActionType.MEASURE,
        LoopName.LOOP_C_KNOWLEDGE: ActionType.ANALYZE,
        LoopName.LOOP_D_COORDINATION: ActionType.CONSOLIDATE,
    }
    
    def __init__(self, workspace_path: Path | None = None) -> None:
        """
        Initialisiert den Loop-Runner.
        
        Args:
            workspace_path: Das Wurzelverzeichnis des Workspaces.
                            Defaults to config.WORKSPACE_ROOT.
        
        Lädt die Zustände aller 4 Schleifen aus 05_Loops/.
        """
        self.workspace_path: Path = (workspace_path or config.WORKSPACE_ROOT).resolve()
        self.loops_dir: Path = self.workspace_path / "05_Loops"
        self.pheromone_field = PheromoneField()
        self.logger = logging.getLogger(__name__)
        
        # Schleifen-Zustände laden oder initialisieren
        self.loop_states: dict[LoopName, LoopState] = {}
        for loop_name in LoopName:
            self.loop_states[loop_name] = self._load_loop_state(loop_name)
    
    def _load_loop_state(self, loop_name: LoopName) -> LoopState:
        """
        Lädt den Zustand einer Schleife aus 05_Loops/{loop_name}.json.
        Falls die Datei nicht existiert, wird ein neuer Zustand erstellt.
        """
        file_path = self.loops_dir / f"{loop_name.value}.json"
        
        if not file_path.exists():
            return LoopState(
                loop_name=loop_name,
                status=LoopStatus.PAUSED,
                energy=100.0,
                last_activity=datetime.now(timezone.utc),
                iteration_count=0,
            )
        
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            return LoopState.model_validate(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning(
                "[LoopRunner] Failed to load state for %s: %s. Creating new state.",
                loop_name.value, exc
            )
            return LoopState(
                loop_name=loop_name,
                status=LoopStatus.PAUSED,
                energy=100.0,
                last_activity=datetime.now(timezone.utc),
                iteration_count=0,
            )
    
    def run_cycle(self) -> LoopCycleResult:
        """
        Führt einen vollständigen Loop-Zyklus aus:
        1. Arbiter-Plan lesen (00_System/arbiter_plan.json)
        2. Basierend auf next_action und loop_priorities die Schleife wählen
        3. Die gewählte Schleife ausführen (Platzhalter!)
        4. Energie-Budget aktualisieren
        5. Pheromon-Feld evaporate() aufrufen (Alterung)
        6. Schleifen-Zustände persistieren
        
        Returns:
            Ein LoopCycleResult mit Statistiken über den Zyklus.
        """
        logger.info("[LoopRunner] Starting loop cycle.")
        
        # 1. Arbiter-Plan lesen
        plan = self._load_arbiter_plan()
        if plan is None:
            logger.warning("[LoopRunner] No arbiter plan found. Using default priorities.")
            # Default-Plan für den Fall, dass keiner existiert
            from src.models.arbiter import ArbiterActionType
            plan = ArbiterPlan(
                directive_summary="(No directive)",
                target_crystal_id="",
                loop_priorities=list(LoopName),
                next_action="explore",
                next_action_reasoning="Default plan",
            )
        
        # 2. Nächste Schleife auswählen
        selected_loop = self.select_next_loop(plan)
        logger.info("[LoopRunner] Selected loop: %s", selected_loop.value)
        
        # 3. Schleife ausführen
        execution_result = self.execute_loop(selected_loop)
        logger.info(
            "[LoopRunner] Executed %s with action %s. Energy change: %.1f → %.1f",
            selected_loop.value, execution_result.action_type,
            execution_result.new_energy - execution_result.energy_change,
            execution_result.new_energy,
        )
        
        # 4. Gesamt-Iterationen berechnen
        total_iterations = sum(
            state.iteration_count for state in self.loop_states.values()
        )
        
        # 5. Pheromon-Feld verdunsten lassen
        evap_result = self.pheromone_field.evaporate()
        logger.info(
            "[LoopRunner] Evaporation complete: %d trails, %d warnings removed.",
            evap_result.trails_evaporated, evap_result.warnings_evaporated,
        )
        
        # 6. Zustände persistieren
        self.save_loop_states()
        
        return LoopCycleResult(
            loop_executed=selected_loop,
            action_type=execution_result.action_type,
            energy_before=execution_result.new_energy - execution_result.energy_change,
            energy_after=execution_result.new_energy,
            energy_change=execution_result.energy_change,
            iterations_total=total_iterations,
            evaporation_stats=evap_result.model_dump(),
        )
    
    def select_next_loop(self, plan: ArbiterPlan) -> LoopName:
        """
        Wählt die nächste Schleife basierend auf dem Arbiter-Plan.
        
        Logik:
        1. Wenn next_action == EXPLORE → erste Schleife in loop_priorities
        2. Wenn next_action == FOLLOW_TRAIL → LOOP_B_EXPERIMENT (dem Trail folgen)
        3. Wenn next_action == DETOUR → erste Schleife in loop_priorities
        4. Wenn next_action == CONSOLIDATE → erste Schleife in loop_priorities
        
        Zusätzliche Regel: Schleifen mit Energie < 30 werden übersprungen,
        es sei denn, alle Schleifen sind < 30 (dann wird die erste gewählt).
        
        Returns:
            Die gewählte LoopName.
        """
        from src.models.arbiter import ArbiterActionType
        
        # Spezialfall: FOLLOW_TRAIL wählt immer LOOP_B_EXPERIMENT
        if plan.next_action == ArbiterActionType.FOLLOW_TRAIL:
            return LoopName.LOOP_B_EXPERIMENT
        
        # Ansonsten: Erste Schleife in loop_priorities wählen
        # Aber: Schleifen mit Energie < 30 überspringen
        low_energy_threshold = 30.0
        
        for loop_name in plan.loop_priorities:
            state = self.loop_states.get(loop_name)
            if state is None:
                continue
            if state.energy >= low_energy_threshold:
                return loop_name
        
        # Falls alle Schleifen < 30 Energie haben, die erste in Prioritäten wählen
        if plan.loop_priorities:
            return plan.loop_priorities[0]
        
        # Fallback: LOOP_A_SIMULATION
        return LoopName.LOOP_A_SIMULATION
    
    def execute_loop(self, loop_name: LoopName) -> LoopExecutionResult:
        """
        Führt eine einzelne Schleife aus.
        
        Diese Methode:
        1. Bestimmt den ActionType basierend auf der Schleife
        2. Nutzt die Kasten-Registry, um die richtige Kaste zu finden
        3. Führt die Kaste mit dem work_dir aus
        4. Aktualisiert das Energie-Budget
        5. Gibt das Ergebnis zurück
        
        Args:
            loop_name: Die Schleife, die ausgeführt werden soll.
        
        Returns:
            Ein LoopExecutionResult mit dem Aktionstyp und der Energie-Änderung.
        """
        from src.castes.registry import get_registry
        
        # 1. ActionType basierend auf der Schleife bestimmen
        action_type = self._get_action_type_for_loop(loop_name)
        
        # 2. Kasten-Registry nutzen, um die richtige Kaste zu finden
        registry = get_registry()
        caste_class = registry.get_caste_for_action(action_type)
        
        # Prüfen, ob es ein Placeholder ist (für Logging)
        is_placeholder = registry.is_placeholder(action_type)
        
        # 3. Kaste instantiieren und ausführen
        caste = caste_class(workspace_path=self.workspace_path)
        
        # work_dir für die Kaste bestimmen
        work_dir = self.workspace_path / "00_System"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "[LoopRunner] Executing %s via %s (placeholder=%s)",
            loop_name.value,
            caste_class.__name__,
            is_placeholder,
        )
        
        # Kaste ausführen
        execution_result = caste.execute(work_dir=work_dir)
        
        # 4. Energie-Budget aktualisieren
        energy_before = self.loop_states[loop_name].energy
        new_energy = self.update_energy(loop_name, action_type)
        energy_change = new_energy - energy_before
        
        # Iterationszähler inkrementieren
        self.loop_states[loop_name].iteration_count += 1
        self.loop_states[loop_name].energy = new_energy
        self.loop_states[loop_name].last_activity = datetime.now(timezone.utc)
        self.loop_states[loop_name].status = LoopStatus.ACTIVE
        
        # 5. Ergebnis zurückgeben
        return LoopExecutionResult(
            loop_name=loop_name,
            action_type=action_type.value,
            energy_change=energy_change,
            new_energy=new_energy,
            iteration_count=self.loop_states[loop_name].iteration_count,
        )


    def _get_action_type_for_loop(self, loop_name: LoopName) -> ActionType:
        """
        Bestimmt den ActionType basierend auf der Schleife.
        
        Mapping:
        - LOOP_A_SIMULATION -> SIMULATE
        - LOOP_B_EXPERIMENT -> MEASURE
        - LOOP_C_KNOWLEDGE -> ANALYZE
        - LOOP_D_COORDINATION -> CONSOLIDATE
        """
        loop_to_action = {
            LoopName.LOOP_A_SIMULATION: ActionType.SIMULATE,
            LoopName.LOOP_B_EXPERIMENT: ActionType.MEASURE,
            LoopName.LOOP_C_KNOWLEDGE: ActionType.ANALYZE,
            LoopName.LOOP_D_COORDINATION: ActionType.CONSOLIDATE,
        }
        return loop_to_action[loop_name]
    
    def update_energy(self, loop_name: LoopName, action_type: ActionType) -> float:
        """
        Aktualisiert das Energie-Budget einer Schleife basierend auf der Aktion.
        
        Args:
            loop_name: Die Schleife, deren Energie aktualisiert wird.
            action_type: Der Typ der ausgeführten Aktion.
        
        Returns:
            Die neue Energie der Schleife (0-100).
        """
        old_state = self.loop_states[loop_name]
        energy_change = self.ENERGY_CHANGES.get(action_type, 0.0)
        new_energy = old_state.energy + energy_change
        
        # Auf [0, 100] kappen
        new_energy = max(0.0, min(100.0, new_energy))
        
        return new_energy
    
    def save_loop_states(self) -> None:
        """
        Schreibt alle Schleifen-Zustände atomar in 05_Loops/.
        
        Für jede Schleife:
        - 05_Loops/{loop_name}.json
        - Atomares Schreiben (temp-Datei + umbenennen)
        """
        self.loops_dir.mkdir(parents=True, exist_ok=True)
        
        for loop_name, state in self.loop_states.items():
            file_path = self.loops_dir / f"{loop_name.value}.json"
            temp_path = file_path.with_suffix(".tmp")
            
            # Atomares Schreiben
            temp_path.write_text(
                state.model_dump_json(indent=2),
                encoding="utf-8",
            )
            temp_path.replace(file_path)
        
        logger.info("[LoopRunner] Saved all loop states to %s", self.loops_dir)
    
    def _load_arbiter_plan(self) -> ArbiterPlan | None:
        """Lädt den Arbiter-Plan aus 00_System/arbiter_plan.json."""
        plan_path = config.ARBITER_PLAN_FILE
        if not plan_path.exists():
            return None
        
        try:
            raw = json.loads(plan_path.read_text(encoding="utf-8"))
            return ArbiterPlan.model_validate(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("[LoopRunner] Failed to load arbiter plan: %s", exc)
            return None
    
    def run_full_loop(self, loop_name: LoopName) -> list[LoopExecutionResult]:
        """
        Führt eine vollständige Schleife aus: alle ActionTypes in Sequenz.
        
        Args:
            loop_name: Der Name der Schleife.
        
        Returns:
            Eine Liste von LoopExecutionResults, eines pro ActionType.
        """
        action_sequence = get_loop_definition(loop_name)
        
        if not action_sequence:
            self.logger.warning(
                "[LoopRunner] Loop %s has no action sequence defined", loop_name.value
            )
            return []
        
        results: list[LoopExecutionResult] = []
        
        for action_type in action_sequence:
            # Prüfe, ob die Schleife noch genug Energie hat
            current_energy = self.loop_states[loop_name].energy
            if current_energy <= 0:
                self.logger.warning(
                    "[LoopRunner] Loop %s has no energy left (%.1f), stopping early",
                    loop_name.value, current_energy
                )
                break
            
            # Führe die einzelne Aktion mit dem spezifischen ActionType aus
            result = self.execute_loop_with_action(loop_name, action_type)
            results.append(result)
            
            # Prüfe, ob die Kaste erfolgreich war
            if not result:
                self.logger.warning(
                    "[LoopRunner] Action %s in loop %s failed, stopping early",
                    action_type.value, loop_name.value
                )
                break
        
        return results
    
    def execute_loop_with_action(self, loop_name: LoopName, action_type: ActionType) -> LoopExecutionResult:
        """
        Führt eine Schleife mit einem spezifischen ActionType aus.
        
        Args:
            loop_name: Die Schleife, die ausgeführt werden soll.
            action_type: Der ActionType, der ausgeführt werden soll.
        
        Returns:
            Ein LoopExecutionResult mit dem Aktionstyp und der Energie-Änderung.
        """
        from src.castes.registry import get_registry
        
        # Kasten-Registry nutzen, um die richtige Kaste zu finden
        registry = get_registry()
        caste_class = registry.get_caste_for_action(action_type)
        
        # Prüfen, ob es ein Placeholder ist (für Logging)
        is_placeholder = registry.is_placeholder(action_type)
        
        # Kaste instantiieren und ausführen
        caste = caste_class(workspace_path=self.workspace_path)
        
        # work_dir für die Kaste bestimmen
        work_dir = self.workspace_path / "00_System"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "[LoopRunner] Executing %s via %s (action=%s, placeholder=%s)",
            loop_name.value,
            caste_class.__name__,
            action_type.value,
            is_placeholder,
        )
        
        # Kaste ausführen
        execution_result = caste.execute(work_dir=work_dir)
        
        # Energie-Budget aktualisieren
        energy_before = self.loop_states[loop_name].energy
        new_energy = self.update_energy(loop_name, action_type)
        energy_change = new_energy - energy_before
        
        # Iterationszähler inkrementieren
        self.loop_states[loop_name].iteration_count += 1
        self.loop_states[loop_name].energy = new_energy
        self.loop_states[loop_name].last_activity = datetime.now(timezone.utc)
        self.loop_states[loop_name].status = LoopStatus.ACTIVE
        
        # Ergebnis zurückgeben
        return LoopExecutionResult(
            loop_name=loop_name,
            action_type=action_type.value,
            energy_change=energy_change,
            new_energy=new_energy,
            iteration_count=self.loop_states[loop_name].iteration_count,
        )

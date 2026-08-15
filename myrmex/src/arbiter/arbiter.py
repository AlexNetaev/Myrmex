"""
src/arbiter/arbiter.py
Die Haupt-Klasse des Arbiters — der Kompass des Schwarms.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.arbiter.landscape import LandscapeAnalyzer
from src.arbiter.decision import DecisionEngine
from src.pheromones.pheromone_field import PheromoneField
from src.models.arbiter import ArbiterPlan, ArbiterActionType, ArbiterCycleResult
from src.models.directive import Directive, TargetCrystal
from src.models.landscape import LandscapeSummary
from src.models.loop import LoopName
import config

logger = logging.getLogger(__name__)


class Arbiter:
    """
    Der Arbiter — der Kompass des Schwarms.
    
    Der Arbiter ist der einzige Agent mit globaler Sicht. Er:
    1. Liest die Pheromon-Landschaft (über LandscapeAnalyzer)
    2. Liest die Directive und den Ziel-Kristall
    3. Entscheidet die nächste Aktion (über DecisionEngine)
    4. Schreibt den Plan (arbiter_plan.json)
    
    Wichtig: Der Arbiter ist stateless. Sein "State" ist die Datei
    arbiter_plan.json. Er macht in dieser Phase keine LLM-Aufrufe —
    alle Entscheidungen sind rein deterministisch.
    """
    
    def __init__(self, workspace_path: Path | None = None) -> None:
        self.workspace_path: Path = (workspace_path or config.WORKSPACE_ROOT).resolve()
        self.pheromone_field = PheromoneField(field_root=self.workspace_path / "01_Pheromon_Field")
        self.landscape_analyzer = LandscapeAnalyzer(self.pheromone_field)
        self.decision_engine = DecisionEngine()
        self.logger = logging.getLogger(__name__)
    
    def run_cycle(self, loop_runner=None) -> ArbiterPlan | ArbiterCycleResult:
        """
        Führt einen vollständigen Arbiter-Zyklus aus.
        
        Wenn loop_runner bereitgestellt wird, führt dies den LoopRunner aus
        und gibt ein ArbiterCycleResult zurück. Andernfalls wird nur der
        Plan geschrieben und ein ArbiterPlan zurückgegeben.
        
        Args:
            loop_runner: Der LoopRunner, der die Schleifen ausführt (optional).
        
        Returns:
            Ein ArbiterPlan (wenn kein loop_runner) oder ArbiterCycleResult (mit loop_runner).
        """
        # 1. Landschaft analysieren
        landscape = self.landscape_analyzer.analyze()
        
        # 2. Directive und Ziel-Kristall lesen
        directive = self._load_directive()
        target_crystal = self._load_target_crystal()
        
        # 3. Aktuellen Plan laden (für revision_count)
        current_plan = self._load_current_plan()
        revision_count = current_plan.revision_count + 1 if current_plan else 0
        
        # 4. Entscheidung treffen
        action, reasoning, loop_priorities = self.decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=current_plan,
        )
        logger.info("[Arbiter] Decision: %s | %s", action.value, reasoning)
        
        # 5. Neuen Plan erstellen
        new_plan = ArbiterPlan(
            directive_summary=self._summarize_directive(directive),
            target_crystal_id=target_crystal.id if target_crystal else "",
            loop_priorities=loop_priorities,
            next_action=action,
            next_action_reasoning=reasoning,
            created_at=datetime.now(timezone.utc),
            revision_count=revision_count,
        )
        
        # 6. Plan schreiben
        self._write_plan(new_plan)
        logger.info("[Arbiter] Plan written (revision %d).", revision_count)
        
        # 7. Wenn loop_runner bereitgestellt ist, führe die Schleife aus
        if loop_runner is not None:
            # Schleife auswählen
            loop_name = self._select_loop_for_action(action, loop_priorities)
            
            self.logger.info(
                "[Arbiter] Executing loop %s (action=%s)",
                loop_name.value, action.value
            )
            loop_results = loop_runner.run_full_loop(loop_name)
            
            return ArbiterCycleResult(
                action=action,
                reasoning=reasoning,
                loop_name=loop_name,
                loop_results=loop_results,
                landscape_summary=self._build_landscape_summary(landscape),
            )
        
        return new_plan
    
    def _select_loop_for_action(self, action: ArbiterActionType, loop_priorities: list[LoopName]) -> LoopName:
        """
        Wählt die Schleife aus, die für die gegebene Aktion ausgeführt werden soll.
        
        Mapping:
        - EXPLORE → LOOP_B_EXPERIMENT (neue Experimente planen)
        - FOLLOW_TRAIL → LOOP_B_EXPERIMENT (einem Trail folgen)
        - DETOUR → LOOP_A_SIMULATION (Simulation anpassen)
        - CONSOLIDATE → LOOP_C_KNOWLEDGE (Wissen konsolidieren)
        """
        action_to_loop = {
            ArbiterActionType.EXPLORE: LoopName.LOOP_B_EXPERIMENT,
            ArbiterActionType.FOLLOW_TRAIL: LoopName.LOOP_B_EXPERIMENT,
            ArbiterActionType.DETOUR: LoopName.LOOP_A_SIMULATION,
            ArbiterActionType.CONSOLIDATE: LoopName.LOOP_C_KNOWLEDGE,
        }
        return action_to_loop.get(action, LoopName.LOOP_B_EXPERIMENT)
    
    def _build_landscape_summary(self, landscape: LandscapeSummary) -> dict:
        """Baut eine Zusammenfassung der Landschaft für das Ergebnis."""
        return {
            "trail_count": landscape.trail_count,
            "crystal_count": landscape.crystal_count,
            "warning_count": landscape.warning_count,
            "total_count": landscape.total_count,
            "is_sparse": landscape.is_sparse,
            "has_strong_trail": landscape.has_strong_trail,
            "has_warning_nearby": landscape.has_warning_nearby,
        }
    
    def _load_directive(self) -> Directive | None:
        """Lädt die Directive aus 00_System/directive.md (als Text, nicht als Modell)."""
        directive_path = self.workspace_path / "00_System" / "directive.md"
        if not directive_path.exists():
            logger.warning("[Arbiter] directive.md not found at %s", directive_path)
            return None
        
        text = directive_path.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning("[Arbiter] directive.md is empty")
            return None
        
        # Hinweis: Die Directive wird hier nur als Text gelesen, nicht als Pydantic-Modell.
        # Das Directive-Modell in src/models/directive.py ist für die strukturierte
        # Repräsentation, aber der Arbiter braucht nur die Zusammenfassung.
        # Wir erzeugen ein minimales Directive-Objekt für die Kompatibilität.
        return Directive(
            title="Current Directive",
            description=text,
            success_criteria=[],
            constraints=[],
        )
    
    def _load_target_crystal(self) -> TargetCrystal | None:
        """Lädt den Ziel-Kristall aus 00_System/target_crystal.json."""
        target_path = self.workspace_path / "00_System" / "target_crystal.json"
        if not target_path.exists():
            return None
        
        try:
            raw = json.loads(target_path.read_text(encoding="utf-8"))
            return TargetCrystal.model_validate(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("[Arbiter] Failed to load target_crystal.json: %s", exc)
            return None
    
    def _load_current_plan(self) -> ArbiterPlan | None:
        """Lädt den aktuellen Plan aus 00_System/arbiter_plan.json."""
        plan_path = self.workspace_path / "00_System" / "arbiter_plan.json"
        if not plan_path.exists():
            return None
        
        try:
            raw = json.loads(plan_path.read_text(encoding="utf-8"))
            return ArbiterPlan.model_validate(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("[Arbiter] Failed to load arbiter_plan.json: %s", exc)
            return None
    
    def _summarize_directive(self, directive: Directive | None) -> str:
        """Erzeugt eine kurze Zusammenfassung der Directive."""
        if directive is None:
            return "(No directive set)"
        
        # Erste 200 Zeichen der Beschreibung als Zusammenfassung
        summary = directive.description[:200]
        if len(directive.description) > 200:
            summary += "..."
        return summary
    
    def _write_plan(self, plan: ArbiterPlan) -> None:
        """Schreibt den Plan atomar in 00_System/arbiter_plan.json."""
        plan_path = self.workspace_path / "00_System" / "arbiter_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomares Schreiben: erst in temp-Datei, dann umbenennen
        temp_path = plan_path.with_suffix(".tmp")
        temp_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(plan_path)
        
        logger.info("[Arbiter] Wrote plan to %s", plan_path)

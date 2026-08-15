"""
src/castes/hypothesizer.py
Die HypothesizerCaste — generiert Hypothesen aus Analyse-Ergebnissen.

Sie ist das letzte Glied in der Schleife B (Experiment-Iteration):
Analyst → Hypothesizer → Planner → Executor → Analyst

In Phase 1 ist die HypothesizerCaste rein deterministisch (kein LLM):
Sie liest TRAIL-Pheromone mit Analyse-Tags, erkennt einfache Muster,
und formuliert daraus strukturierte Hypothesen. Eine LLM-basierte,
intelligentere Hypothesen-Generierung kann in einer späteren Phase
ergänzt werden.

Die HypothesizerCaste liest auch die theory_baseline.md für den
wissenschaftlichen Kontext, und schreibt ihre Hypothesen sowohl als
TRAIL-Pheromon (Tag "hypothesis") ins Feld als auch als hypothesis.md
für die Nachvollziehbarkeit.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType

logger = logging.getLogger("caste.hypothesizer")


class HypothesizerCaste(BaseCaste):
    """
    Die HypothesizerCaste — generiert Hypothesen aus Analyse-Ergebnissen.
    """
    
    caste_name = CasteName.HYPOTHESIZER
    role = "Hypothesen aus Diskrepanzen und Mustern generieren"
    specialization = "Deterministische Mustererkennung und Hypothesenformulierung"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]
    
    HYPOTHESIS_FILENAME = "hypothesis.md"
    KNOWLEDGE_BASE_DIR_NAME = "04_Knowledge_Base"
    THEORY_BASELINE_FILENAME = "theory_baseline.md"
    
    # Tags, die als "Analyse-Ergebnisse" gelten und als Input für Hypothesen dienen
    ANALYSIS_TAGS = {"analysis", "discrepancy", "simulation", "finding"}
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Hypothesen-Generierung aus:
        1. Liest TRAIL-Pheromone mit Analyse-Tags aus dem Feld.
        2. Liest die theory_baseline.md für den Kontext.
        3. Generiert eine Hypothese basierend auf den Mustern.
        4. Schreibt die Hypothese als hypothesis.md und als TRAIL-Pheromon.
        """
        self.logger.info("[%s] Starting hypothesis generation", self.caste_name.value)
        
        # 1. Analyse-Pheromone lesen
        analysis_pheromones = self._collect_analysis_pheromones()
        
        if not analysis_pheromones:
            self.logger.info("[%s] No analysis pheromones to generate hypotheses from", self.caste_name.value)
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={"reason": "no_analysis_pheromones"},
            )
        
        # 2. Theorie-Baseline lesen für den Kontext
        theory_context = self._read_theory_baseline()
        
        # 3. Hypothese generieren (deterministisch in Phase 1)
        hypothesis = self._generate_hypothesis(analysis_pheromones, theory_context)
        
        # 4. Hypothese schreiben (hypothesis.md + TRAIL-Pheromon)
        hypothesis_path = self._write_hypothesis_file(work_dir, hypothesis)
        
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=hypothesis["summary"],
            tags=["hypothesis", "experiment_iteration"],
            strength=0.6,
            relevance=0.8,
        )
        
        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=len(analysis_pheromones),
            pheromones_written=1,
            output_files=[self.HYPOTHESIS_FILENAME],
            extra_data={
                "hypothesis_count": 1,
                "analysis_pheromones_used": len(analysis_pheromones),
                "pheromone_id": pheromone.id,
                "hypothesis_path": str(hypothesis_path),
            },
        )
    
    def _collect_analysis_pheromones(self) -> list:
        """
        Sammelt TRAIL-Pheromone, die mindestens einen Analyse-Tag haben.
        """
        all_trails = self.read_pheromones(pheromone_type=PheromoneType.TRAIL)
        
        analysis_pheromones = []
        for pheromone in all_trails:
            if any(tag in self.ANALYSIS_TAGS for tag in pheromone.tags):
                analysis_pheromones.append(pheromone)
        
        return analysis_pheromones
    
    def _read_theory_baseline(self) -> str:
        """
        Liest die theory_baseline.md für den wissenschaftlichen Kontext.
        Gibt einen leeren String zurück, wenn die Datei nicht existiert.
        """
        theory_path = self.workspace_path / self.KNOWLEDGE_BASE_DIR_NAME / self.THEORY_BASELINE_FILENAME
        
        if not theory_path.exists():
            return ""
        
        try:
            return theory_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.warning("[%s] Could not read theory_baseline.md: %s", self.caste_name.value, e)
            return ""
    
    def _generate_hypothesis(self, analysis_pheromones: list, theory_context: str) -> dict:
        """
        Generiert eine Hypothese basierend auf den Analyse-Pheromonen.
        
        In Phase 1 ist dies deterministisch: Die Hypothese wird aus den
        Inhalten der Analyse-Pheromone zusammengesetzt. Eine LLM-basierte
        Generierung kann in einer späteren Phase ergänzt werden.
        
        Returns:
            Ein dict mit 'root_cause_analysis', 'proposed_adjustment' und 'summary'.
        """
        # Sortiere nach Erstellungszeit (älteste zuerst)
        analysis_pheromones.sort(key=lambda p: p.created_at)
        
        # Sammle die Inhalte der Analyse-Pheromone
        findings = []
        for pheromone in analysis_pheromones:
            source = pheromone.source_agent
            tags = ", ".join(pheromone.tags)
            findings.append(f"[{source}] ({tags}): {pheromone.content}")
        
        # Generiere die Hypothese (deterministisch in Phase 1)
        # In einer späteren Phase könnte hier ein LLM-Aufruf stehen
        
        # Einfache Mustererkennung: Wenn es mehrere Analyse-Pheromone gibt,
        # formuliere eine Hypothese über den Zusammenhang
        if len(findings) >= 2:
            root_cause = (
                f"Based on {len(findings)} analysis findings, the observed behavior "
                f"suggests a systematic relationship between the experimental parameters "
                f"and the measured outcome. The findings indicate: "
                f"{'; '.join(findings[:3])}"
            )
            proposed_adjustment = (
                "Adjust the primary experimental parameter (e.g., concentration, temperature) "
                "by one step in the direction suggested by the analysis findings, "
                "and observe whether the measured outcome moves closer to the simulated prediction."
            )
        elif len(findings) == 1:
            root_cause = (
                f"Based on a single analysis finding, the observed behavior is: "
                f"{findings[0]}. Further investigation is needed to confirm this pattern."
            )
            proposed_adjustment = (
                "Repeat the experiment with the same parameters to verify the finding, "
                "or adjust one parameter slightly to test sensitivity."
            )
        else:
            root_cause = "No analysis findings available to generate a hypothesis."
            proposed_adjustment = "Run a baseline experiment to gather initial data."
        
        # Zusammenfassung für das Pheromon
        summary = f"Hypothesis: {root_cause[:100]}... Proposed: {proposed_adjustment[:80]}..."
        
        return {
            "root_cause_analysis": root_cause,
            "proposed_adjustment": proposed_adjustment,
            "summary": summary,
            "findings_used": findings,
        }
    
    def _write_hypothesis_file(self, work_dir: Path, hypothesis: dict) -> Path:
        """
        Schreibt die Hypothese als hypothesis.md in das work_dir.
        """
        work_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        findings_block = "\n".join(f"- {f}" for f in hypothesis["findings_used"])
        
        content = f"""# Hypothesis Report

*Generated at {timestamp} by HypothesizerCaste*

## Root Cause Analysis

{hypothesis["root_cause_analysis"]}

## Proposed Adjustment for Next Cycle

{hypothesis["proposed_adjustment"]}

## Analysis Findings Used

{findings_block}
"""
        
        hypothesis_path = work_dir / self.HYPOTHESIS_FILENAME
        hypothesis_path.write_text(content, encoding="utf-8")
        
        self.logger.info("[%s] Wrote hypothesis to %s", self.caste_name.value, hypothesis_path)
        
        return hypothesis_path

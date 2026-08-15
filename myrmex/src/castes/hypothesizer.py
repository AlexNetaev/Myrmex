"""
src/castes/hypothesizer.py
Die HypothesizerCaste — generiert Hypothesen aus Analyse-Ergebnissen.

Sie ist das letzte Glied in der Schleife B (Experiment-Iteration):
Analyst → Hypothesizer → Planner → Executor → Analyst

In dieser Version nutzt sie ein LLM für die eigentliche Hypothesen-
Generierung. Die bestehende deterministische Logik bleibt als Fallback
erhalten, falls das LLM nicht verfügbar ist.

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
from src.castes.hypothesis_models import HypothesisModel

logger = logging.getLogger("caste.hypothesizer")

# LLM-Konfiguration
OLLAMA_MODEL = "gemma4:31b-cloud"
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_CONTEXT_SIZE = 4096


class HypothesizerCaste(BaseCaste):
    """
    Die HypothesizerCaste — generiert Hypothesen aus Analyse-Ergebnissen.
    
    In dieser Version nutzt sie ein LLM für die eigentliche Hypothesen-
    Generierung. Die bestehende deterministische Logik bleibt als Fallback
    erhalten, falls das LLM nicht verfügbar ist.
    """

    caste_name = CasteName.HYPOTHESIZER
    role = "Hypothesen aus Diskrepanzen und Mustern generieren"
    specialization = "LLM-basierte Hypothesen-Generierung mit deterministischem Fallback"
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
        3. Versucht die LLM-basierte Generierung.
        4. Falls LLM fehlschlägt: Verwendet den deterministischen Fallback.
        5. Schreibt die Hypothese als hypothesis.md und als TRAIL-Pheromon.
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

        # 3. LLM-basierte Generierung versuchen
        hypothesis = None
        llm_used = False
        try:
            hypothesis = self._generate_hypothesis_with_llm(analysis_pheromones, theory_context)
            llm_used = True
            self.logger.info("[%s] LLM-based hypothesis generated successfully", self.caste_name.value)
        except Exception as e:
            self.logger.warning(
                "[%s] LLM-based hypothesis generation failed: %s. "
                "Falling back to deterministic logic.",
                self.caste_name.value, e
            )

        # 4. Fallback: Deterministische Generierung
        if hypothesis is None:
            hypothesis = self._generate_hypothesis_deterministic(analysis_pheromones, theory_context)
            llm_used = False

        # 5. Hypothese schreiben (hypothesis.md + TRAIL-Pheromon)
        hypothesis_path = self._write_hypothesis_file(work_dir, hypothesis, llm_used)

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
                "llm_used": llm_used,
                "confidence": hypothesis.get("confidence", "unknown"),
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
    
    def _generate_hypothesis_with_llm(self, analysis_pheromones: list, theory_context: str) -> dict:
        """
        Generiert eine Hypothese mit dem LLM.
        
        Args:
            analysis_pheromones: Die Analyse-Pheromone als Input.
            theory_context: Die Theorie-Baseline für den Kontext.
        
        Returns:
            Ein dict mit 'root_cause_analysis', 'proposed_adjustment',
            'testable_prediction', 'confidence' und 'summary'.
        
        Raises:
            Exception: Wenn das LLM nicht verfügbar ist oder keine gültige
                       Antwort gibt.
        """
        # Pheromon-Inhalte sammeln
        findings = []
        for pheromone in analysis_pheromones:
            source = pheromone.source_agent
            tags = ", ".join(pheromone.tags)
            findings.append(f"[{source}] ({tags}): {pheromone.content}")

        findings_text = "\n".join(f"- {f}" for f in findings)

        # Prompt erstellen
        prompt = f"""You are the Hypothesizer for an autonomous self-driving laboratory.
Your task is to generate a scientific hypothesis based on the analysis findings
and the current theory baseline.

Analysis Findings (from recent experiments):
{findings_text}

Current Theory Baseline (theory_baseline.md):
{theory_context}

Your task:
1. Analyze the findings and identify the most likely causal relationship.
2. Propose a concrete adjustment for the next experiment.
3. Formulate a testable prediction.
4. Assess your confidence in the hypothesis.
5. Provide a short summary (max. 200 characters).

Be specific and actionable. Avoid vague statements like "further investigation needed".
Instead, propose concrete parameter changes and measurable predictions.
"""

        system_prompt = (
            "You are the Hypothesizer for an autonomous self-driving laboratory. "
            "You generate scientific hypotheses based on experimental data and "
            "theoretical knowledge. Your hypotheses must be testable, specific, "
            "and actionable. Avoid vague or generic statements."
        )

        # LLM aufrufen (hier muss die ask_llm-Funktion verwendet werden)
        # Die genaue Implementierung hängt von der BaseCaste ab
        result = self.ask_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            response_model=HypothesisModel,
            max_retries=DEFAULT_MAX_RETRIES,
            temperature=DEFAULT_TEMPERATURE,
            context_size=DEFAULT_CONTEXT_SIZE,
        )

        # Ergebnis in dict umwandeln
        return {
            "root_cause_analysis": result.root_cause_analysis,
            "proposed_adjustment": result.proposed_adjustment,
            "testable_prediction": result.testable_prediction,
            "confidence": result.confidence,
            "summary": result.summary,
        }

    def _generate_hypothesis_deterministic(self, analysis_pheromones: list, theory_context: str) -> dict:
        """
        Deterministischer Fallback für die Hypothesen-Generierung.
        Dies ist die bestehende Logik aus Phase 1.
        """
        # Sortiere nach Erstellungszeit (älteste zuerst)
        analysis_pheromones.sort(key=lambda p: p.created_at)

        # Sammle die Inhalte der Analyse-Pheromone
        findings = []
        for pheromone in analysis_pheromones:
            source = pheromone.source_agent
            tags = ", ".join(pheromone.tags)
            findings.append(f"[{source}] ({tags}): {pheromone.content}")

        # Generiere die Hypothese (deterministisch)
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
            testable_prediction = (
                "If the hypothesis is correct, the next experiment should show a measurable "
                "change in the target parameter in the predicted direction."
            )
            confidence = "medium"
        elif len(findings) == 1:
            root_cause = (
                f"Based on a single analysis finding, the observed behavior is: "
                f"{findings[0]}. Further investigation is needed to confirm this pattern."
            )
            proposed_adjustment = (
                "Repeat the experiment with the same parameters to verify the finding, "
                "or adjust one parameter slightly to test sensitivity."
            )
            testable_prediction = (
                "If the finding is correct, repeating the experiment should produce "
                "similar results."
            )
            confidence = "low"
        else:
            root_cause = "No analysis findings available to generate a hypothesis."
            proposed_adjustment = "Run a baseline experiment to gather initial data."
            testable_prediction = (
                "The baseline experiment should produce measurable data."
            )
            confidence = "low"

        # Zusammenfassung für das Pheromon
        summary = f"Hypothesis: {root_cause[:100]}... Proposed: {proposed_adjustment[:80]}..."

        return {
            "root_cause_analysis": root_cause,
            "proposed_adjustment": proposed_adjustment,
            "testable_prediction": testable_prediction,
            "confidence": confidence,
            "summary": summary,
            "findings_used": findings,
        }

    def _write_hypothesis_file(self, work_dir: Path, hypothesis: dict, llm_used: bool) -> Path:
        """
        Schreibt die Hypothese als hypothesis.md in das work_dir.
        """
        work_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        source = "LLM (gemma4:31b-cloud)" if llm_used else "Deterministic Fallback"

        findings_block = ""
        if "findings_used" in hypothesis:
            findings_block = "\n".join(f"- {f}" for f in hypothesis["findings_used"])
            findings_block = f"\n## Analysis Findings Used\n\n{findings_block}\n"

        content = f"""# Hypothesis Report

*Generated at {timestamp} by HypothesizerCaste ({source})*

## Root Cause Analysis

{hypothesis["root_cause_analysis"]}

## Proposed Adjustment for Next Cycle

{hypothesis["proposed_adjustment"]}

## Testable Prediction

{hypothesis["testable_prediction"]}

## Confidence

{hypothesis["confidence"]}
{findings_block}
"""
        hypothesis_path = work_dir / self.HYPOTHESIS_FILENAME
        hypothesis_path.write_text(content, encoding="utf-8")
        self.logger.info("[%s] Wrote hypothesis to %s", self.caste_name.value, hypothesis_path)
        return hypothesis_path

    # Die bestehenden Methoden _collect_analysis_pheromones und
    # _read_theory_baseline bleiben unverändert.

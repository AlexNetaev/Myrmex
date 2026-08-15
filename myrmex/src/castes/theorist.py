"""
src/castes/theorist.py
Die TheoristCaste — das Langzeitgedächtnis des Schwarms.

Ersetzt die PlaceholderCaste für die CONSOLIDATE-Aktion. Sie liest
TRAIL-Pheromone aus dem Pheromon-Feld und konsolidiert sie strukturiert
in die theory_baseline.md (im 04_Knowledge_Base/-Verzeichnis).

In dieser Version nutzt sie ein LLM für die intelligente Konsolidierung.
Die bestehende deterministische Logik bleibt als Fallback erhalten.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType
from src.castes.consolidation_models import ConsolidationModel, ContradictionResolution

logger = logging.getLogger("caste.theorist")

# LLM-Konfiguration (identisch zu HypothesizerCaste und AnalystCaste)
OLLAMA_MODEL = "gemma4:31b-cloud"
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_CONTEXT_SIZE = 4096


class TheoristCaste(BaseCaste):
    """
    Die TheoristCaste — konsolidiert Erkenntnisse in die theory_baseline.md.
    
    In dieser Version nutzt sie ein LLM für die intelligente Konsolidierung.
    Die bestehende deterministische Logik bleibt als Fallback erhalten.
    """

    caste_name = CasteName.THEORIST
    role = "Erkenntnisse in das Langzeitgedächtnis konsolidieren"
    specialization = "LLM-basierte Wissens-Konsolidierung mit deterministischem Fallback"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]

    THEORY_BASELINE_FILENAME = "theory_baseline.md"
    KNOWLEDGE_BASE_DIR_NAME = "04_Knowledge_Base"

    # Tags, die als "Erkenntnisse" gelten und konsolidiert werden
    KNOWLEDGE_TAGS = {"analysis", "simulation", "finding", "hypothesis"}

    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Konsolidierung aus:
        1. Liest TRAIL-Pheromone mit Knowledge-Tags aus dem Feld.
        2. Liest die theory_baseline.md für den Kontext.
        3. Versucht die LLM-basierte Konsolidierung.
        4. Falls LLM fehlschlägt: Verwendet deterministischen Fallback.
        5. Aktualisiert die theory_baseline.md.
        6. Schreibt ein TRAIL-Pheromon als Bestätigung.
        """
        self.logger.info("[%s] Starting consolidation", self.caste_name.value)

        # 1. TRAIL-Pheromone mit Knowledge-Tags lesen
        knowledge_pheromones = self._collect_knowledge_pheromones()

        if not knowledge_pheromones:
            self.logger.info("[%s] No knowledge pheromones to consolidate", self.caste_name.value)
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={"reason": "no_knowledge_pheromones"},
            )

        # 2. Nach Erstellungszeit sortieren (älteste zuerst)
        knowledge_pheromones.sort(key=lambda p: p.created_at)

        # 3. Theorie-Baseline lesen
        theory_path = self._get_theory_baseline_path()
        theory_context = self._read_theory_baseline()

        # 4. LLM-basierte Konsolidierung versuchen
        consolidation = None
        llm_used = False
        try:
            consolidation = self._consolidate_with_llm(knowledge_pheromones, theory_context)
            llm_used = True
            self.logger.info("[%s] LLM-based consolidation completed successfully", self.caste_name.value)
        except Exception as e:
            self.logger.warning(
                "[%s] LLM-based consolidation failed: %s. Falling back to deterministic logic.",
                self.caste_name.value, e,
            )

        # 5. Fallback: Deterministische Konsolidierung
        if consolidation is None:
            consolidation = self._consolidate_deterministic(knowledge_pheromones)
            llm_used = False

        # 6. theory_baseline.md aktualisieren
        entries_added = self._update_theory_baseline(theory_path, consolidation, llm_used)

        # 7. TRAIL-Pheromon als Bestätigung schreiben
        summary = (
            f"Theorist consolidated {entries_added} knowledge entries into theory_baseline.md "
            f"({'LLM' if llm_used else 'deterministic'})"
        )
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=summary,
            tags=["consolidation", "theory"],
            strength=0.4,
            relevance=0.5,
        )

        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=len(knowledge_pheromones),
            pheromones_written=1,
            output_files=[self.THEORY_BASELINE_FILENAME],
            extra_data={
                "entries_added": entries_added,
                "pheromone_id": pheromone.id,
                "theory_path": str(theory_path),
                "llm_used": llm_used,
                "confidence": consolidation.get("confidence", "unknown"),
                "contradictions_resolved": len(consolidation.get("contradictions_resolved", [])),
            },
        )

    def _consolidate_with_llm(self, knowledge_pheromones: list, theory_context: str) -> dict:
        """
        Führt die LLM-basierte Konsolidierung durch.
        """
        # Pheromon-Inhalte sammeln
        findings = []
        for pheromone in knowledge_pheromones:
            source = pheromone.source_agent
            tags = ", ".join(pheromone.tags)
            timestamp = pheromone.created_at.isoformat()
            findings.append(f"[{timestamp}] [{source}] ({tags}): {pheromone.content}")

        findings_text = "\n".join(findings)

        prompt = f"""You are the Theorist for an autonomous self-driving laboratory.
Your task is to consolidate new experimental findings into the theory baseline.

## Current Theory Baseline (theory_baseline.md):
{theory_context}

## New Findings (from recent experiments):
{findings_text}

## Your Task:
1. Integrate the new findings into the theory baseline.
2. Identify any contradictions between new findings and existing knowledge.
3. Resolve contradictions scientifically (explain which version is correct and why).
4. Identify any existing knowledge that is now deprecated by the new findings.
5. Write a coherent, structured summary of the new knowledge to append to the baseline.
6. Assess your confidence in the consolidation ('high', 'medium', 'low').

## IMPORTANT: Output Format
You MUST respond with ONLY a JSON object. No markdown, no explanations, no code blocks.
Use this exact JSON schema:

{{
  "summary": "Short summary of the consolidation",
  "new_knowledge": "Structured new knowledge to append",
  "contradictions_resolved": [
    {{"old_knowledge": "...", "new_knowledge": "...", "resolution": "..."}}
  ],
  "deprecated_knowledge": ["List of deprecated statements"],
  "confidence": "high"
}}

Remember: ONLY the JSON object. No other text.
Be scientifically rigorous. Use clear, precise language. Avoid vague statements.
"""

        system_prompt = (
            "You are the Theorist for an autonomous self-driving laboratory. "
            "You consolidate experimental findings into a coherent theory baseline, "
            "resolving contradictions and maintaining scientific rigor. You MUST "
            "respond with ONLY a valid JSON object. No markdown, no explanations, "
            "no code blocks. Just the raw JSON object."
        )

        # LLM aufrufen
        result = self.ask_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            response_model=ConsolidationModel,
            max_retries=DEFAULT_MAX_RETRIES,
            temperature=DEFAULT_TEMPERATURE,
            context_size=DEFAULT_CONTEXT_SIZE,
        )

        # In dict umwandeln
        return {
            "summary": result.summary,
            "new_knowledge": result.new_knowledge,
            "contradictions_resolved": [c.model_dump() for c in result.contradictions_resolved],
            "deprecated_knowledge": result.deprecated_knowledge,
            "confidence": result.confidence,
        }

    def _consolidate_deterministic(self, knowledge_pheromones: list) -> dict:
        """
        Deterministischer Fallback für die Konsolidierung.
        Dies ist die bestehende Logik aus Phase 1 (einfaches Anhängen).
        """
        # Sammle die Inhalte der Pheromone
        findings = []
        for pheromone in knowledge_pheromones:
            source = pheromone.source_agent
            tags = ", ".join(pheromone.tags)
            findings.append(f"[{source}] ({tags}): {pheromone.content}")

        # Generiere die Konsolidierung (deterministisch)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        new_knowledge = f"## Consolidation ({timestamp})\n"
        for finding in findings:
            new_knowledge += f"- {finding}\n"

        summary = f"Consolidated {len(findings)} findings into theory_baseline.md"

        return {
            "summary": summary,
            "new_knowledge": new_knowledge,
            "contradictions_resolved": [],
            "deprecated_knowledge": [],
            "confidence": "medium",
        }

    def _update_theory_baseline(self, theory_path: Path, consolidation: dict, llm_used: bool) -> int:
        """
        Aktualisiert die theory_baseline.md mit der Konsolidierung.
        Gibt die Anzahl der hinzugefügten Einträge zurück.
        """
        # Theorie-Baseline initialisieren, falls sie nicht existiert
        if not theory_path.exists():
            theory_path.write_text(
                "# Theory Baseline\n\n*(Consolidated knowledge from the swarm.)*\n",
                encoding="utf-8",
            )

        # Neuen Konsolidierungs-Block anhängen
        with theory_path.open("a", encoding="utf-8") as f:
            f.write(f"\n{consolidation['new_knowledge']}\n")

        # Wenn LLM verwendet wurde und Widersprüche aufgelöst wurden,
        # schreibe eine separate Datei für die Audit-Trail
        if llm_used and consolidation.get("contradictions_resolved"):
            self._write_contradiction_report(theory_path, consolidation)

        # Zähle die Anzahl der Einträge (approximativ)
        return len(consolidation["new_knowledge"].split("\n")) - 1

    def _write_contradiction_report(self, theory_path: Path, consolidation: dict) -> None:
        """
        Schreibt einen separaten Bericht über aufgelöste Widersprüche.
        """
        contradiction_report_path = theory_path.parent / "contradiction_resolutions.md"
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        report = f"# Contradiction Resolutions Report\n\n*Generated at {timestamp}*\n\n"
        
        for i, contradiction in enumerate(consolidation["contradictions_resolved"], 1):
            report += f"## Contradiction {i}\n\n"
            report += f"**Old Knowledge:**\n{contradiction['old_knowledge']}\n\n"
            report += f"**New Knowledge:**\n{contradiction['new_knowledge']}\n\n"
            report += f"**Resolution:**\n{contradiction['resolution']}\n\n"
            report += "---\n\n"
        
        contradiction_report_path.write_text(report, encoding="utf-8")
        self.logger.info(
            "[%s] Wrote contradiction report to %s",
            self.caste_name.value, contradiction_report_path
        )

    def _collect_knowledge_pheromones(self) -> list:
        """
        Sammelt TRAIL-Pheromone, die mindestens einen Knowledge-Tag haben.
        """
        all_trails = self.read_pheromones(pheromone_type=PheromoneType.TRAIL)
        
        knowledge_pheromones = []
        for pheromone in all_trails:
            # Ein Pheromon gilt als "Erkenntnis", wenn es mindestens einen
            # der Knowledge-Tags hat
            if any(tag in self.KNOWLEDGE_TAGS for tag in pheromone.tags):
                knowledge_pheromones.append(pheromone)
        
        return knowledge_pheromones

    def _get_theory_baseline_path(self) -> Path:
        """
        Gibt den Pfad zur theory_baseline.md im Knowledge-Base-Verzeichnis zurück.
        Erstellt das Verzeichnis, falls es nicht existiert.
        """
        knowledge_base_dir = self.workspace_path / self.KNOWLEDGE_BASE_DIR_NAME
        knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        return knowledge_base_dir / self.THEORY_BASELINE_FILENAME

    def _read_theory_baseline(self) -> str:
        """
        Liest die theory_baseline.md für den Kontext.
        Gibt einen leeren String zurück, wenn die Datei nicht existiert.
        """
        theory_path = self._get_theory_baseline_path()
        if not theory_path.exists():
            return ""
        return theory_path.read_text(encoding="utf-8")

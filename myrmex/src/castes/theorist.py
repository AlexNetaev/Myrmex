"""
src/castes/theorist.py
Die TheoristCaste — das Langzeitgedächtnis des Schwarms.

Ersetzt die PlaceholderCaste für die CONSOLIDATE-Aktion. Sie liest
TRAIL-Pheromone aus dem Pheromon-Feld und konsolidiert sie strukturiert
in die theory_baseline.md (im 04_Knowledge_Base/-Verzeichnis).

In Phase 1 ist die TheoristCaste rein deterministisch (kein LLM):
Sie sammelt die TRAIL-Pheromone, sortiert sie nach Erstellungszeit,
und hängt sie strukturiert an die theory_baseline.md an. Eine
LLM-basierte, intelligente Konsolidierung kann in einer späteren
Phase ergänzt werden.

Die TheoristCaste ist das Bindeglied zwischen den flüchtigen
TRAIL-Pheromonen (die verdunsten) und der permanenten theory_baseline.md
(die bleibt).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType

logger = logging.getLogger("caste.theorist")


class TheoristCaste(BaseCaste):
    """
    Die TheoristCaste — konsolidiert Erkenntnisse in die theory_baseline.md.
    """
    
    caste_name = CasteName.THEORIST
    role = "Erkenntnisse in das Langzeitgedächtnis konsolidieren"
    specialization = "Deterministische Wissens-Konsolidierung"
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
        2. Sortiert sie nach Erstellungszeit.
        3. Hängt sie strukturiert an die theory_baseline.md an.
        4. Schreibt ein TRAIL-Pheromon als Bestätigung.
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
        
        # 3. An die theory_baseline.md anhängen
        theory_path = self._get_theory_baseline_path()
        entries_added = self._append_to_theory_baseline(theory_path, knowledge_pheromones)
        
        # 4. TRAIL-Pheromon als Bestätigung schreiben
        summary = f"Theorist consolidated {entries_added} knowledge entries into theory_baseline.md"
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
            },
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
    
    def _append_to_theory_baseline(self, theory_path: Path, pheromones: list) -> int:
        """
        Hängt die Erkenntnisse strukturiert an die theory_baseline.md an.
        Gibt die Anzahl der hinzugefügten Einträge zurück.
        """
        # Theorie-Baseline initialisieren, falls sie nicht existiert
        if not theory_path.exists():
            theory_path.write_text(
                "# Theory Baseline\n\n*(Consolidated knowledge from the swarm.)*\n",
                encoding="utf-8",
            )
        
        # Neuen Konsolidierungs-Block erstellen
        timestamp = datetime.now(timezone.utc).isoformat()
        block_lines = [
            f"\n## Consolidation ({timestamp})\n",
        ]
        
        for pheromone in pheromones:
            source = pheromone.source_agent
            tags = ", ".join(pheromone.tags)
            block_lines.append(f"- **[{source}]** ({tags}): {pheromone.content}\n")
        
        block = "".join(block_lines)
        
        # Anhängen
        with theory_path.open("a", encoding="utf-8") as f:
            f.write(block)
        
        return len(pheromones)

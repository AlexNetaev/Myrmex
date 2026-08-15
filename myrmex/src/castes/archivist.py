"""
src/castes/archivist.py
Die ArchivistCaste — Token-Hygiene und Archivierung des Langzeitgedächtnisses.

Ersetzt die PlaceholderCaste für die ARCHIVE-Aktion. Sie ist das letzte
Glied in der Schleife C (Wissens-Aufbau): Analyst → Theorist → Guardian
→ Archivist. Während die TheoristCaste Wissen aufbaut und die GuardianCaste
es validiert, sorgt der Archivist dafür, dass das Langzeitgedächtnis nicht
unbegrenzt wächst.

In Phase 1 ist die ArchivistCaste rein deterministisch (kein LLM):
Sie prüft die Länge der theory_baseline.md. Wenn sie über
MAX_BASELINE_CHARS liegt, identifiziert sie die `## Consolidation`-Blöcke,
verschiebt die ältesten ins Archiv (Archive/theory_archive.md), und behält
nur die neuesten in der aktiven Baseline. Eine LLM-basierte, intelligente
Kompression (echte Zusammenfassung) kann in einer späteren Phase ergänzt
werden.

WICHTIG: Der Archivist löscht niemals Wissen — er verlagert es nur aus der
aktiven Baseline ins permanente Archiv. So geht nichts verloren, aber die
aktive Baseline bleibt klein und schnell lesbar.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType

logger = logging.getLogger("caste.archivist")


class ArchivistCaste(BaseCaste):
    """
    Die ArchivistCaste — Token-Hygiene und Archivierung.
    """

    caste_name = CasteName.ARCHIVIST
    role = "Das Langzeitgedächtnis schlank halten (Token-Hygiene)"
    specialization = "Deterministische Archivierung und Kompression"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL]

    THEORY_BASELINE_FILENAME = "theory_baseline.md"
    THEORY_ARCHIVE_FILENAME = "theory_archive.md"
    KNOWLEDGE_BASE_DIR_NAME = "04_Knowledge_Base"
    ARCHIVE_DIR_NAME = "Archive"

    # Maximale Länge der aktiven theory_baseline.md (in Zeichen).
    # Wenn die Baseline diesen Wert überschreitet, werden die ältesten
    # Consolidation-Blöcke ins Archiv verschoben.
    # Konsistent mit dem Guardian's MAX_BASELINE_CHARS (8000).
    MAX_BASELINE_CHARS = 8000

    # Wie viele der neuesten Consolidation-Blöcke in der aktiven Baseline
    # bleiben sollen, nachdem die ältesten ins Archiv verschoben wurden.
    KEEP_RECENT_BLOCKS = 3

    # Regex, um einen Consolidation-Block zu identifizieren.
    # Ein Block beginnt mit "## Consolidation" und geht bis zum nächsten
    # "## "-Header oder zum Ende der Datei.
    CONSOLIDATION_BLOCK_PATTERN = re.compile(
        r"^## Consolidation.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )

    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Token-Hygiene aus:
        1. Liest die theory_baseline.md und prüft ihre Länge.
        2. Wenn unter MAX_BASELINE_CHARS: Nichts tun.
        3. Wenn über MAX_BASELINE_CHARS: Die ältesten Consolidation-Blöcke
           ins Archiv verschieben und die aktive Baseline kürzen.
        4. Schreibt ein TRAIL-Pheromon mit der Bestätigung.
        """
        self.logger.info("[%s] Starting token hygiene", self.caste_name.value)

        # 1. Pfad zur theory_baseline.md bestimmen
        theory_path = self.workspace_path / self.KNOWLEDGE_BASE_DIR_NAME / self.THEORY_BASELINE_FILENAME

        # 2. Prüfen, ob die Datei existiert
        if not theory_path.exists():
            self.logger.info("[%s] theory_baseline.md not found - nothing to curate", self.caste_name.value)
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={"reason": "no_theory_baseline"},
            )

        # 3. Länge prüfen
        content = theory_path.read_text(encoding="utf-8")
        baseline_length = len(content)

        if baseline_length <= self.MAX_BASELINE_CHARS:
            self.logger.info(
                "[%s] theory_baseline.md is %d/%d chars - within budget, no compression needed",
                self.caste_name.value, baseline_length, self.MAX_BASELINE_CHARS,
            )
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={
                    "reason": "no_compression_needed",
                    "baseline_length": baseline_length,
                },
            )

        # 4. Consolidation-Blöcke identifizieren
        blocks = self._extract_consolidation_blocks(content)

        if len(blocks) <= self.KEEP_RECENT_BLOCKS:
            # Nicht genug Blöcke, um etwas ins Archiv zu verschieben
            self.logger.info(
                "[%s] Only %d consolidation block(s) - not enough to archive (need > %d)",
                self.caste_name.value, len(blocks), self.KEEP_RECENT_BLOCKS,
            )
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={
                    "reason": "not_enough_blocks_to_archive",
                    "baseline_length": baseline_length,
                    "block_count": len(blocks),
                },
            )

        # 5. Älteste Blöcke ins Archiv verschieben
        blocks_to_archive = blocks[: -self.KEEP_RECENT_BLOCKS]
        blocks_to_keep = blocks[-self.KEEP_RECENT_BLOCKS :]

        archive_path = self._get_archive_path()
        self._append_to_archive(archive_path, blocks_to_archive)

        # 6. Aktive Baseline kürzen (nur die neuesten Blöcke behalten)
        self._rewrite_baseline_with_recent_blocks(theory_path, content, blocks_to_keep)

        # 7. TRAIL-Pheromon mit Bestätigung schreiben
        new_length = len(theory_path.read_text(encoding="utf-8"))
        summary = (
            f"Archivist moved {len(blocks_to_archive)} consolidation block(s) to archive. "
            f"Baseline: {baseline_length} -> {new_length} chars."
        )
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=summary,
            tags=["archive", "token_hygiene"],
            strength=0.4,
            relevance=0.5,
        )

        self.logger.info(
            "[%s] Archived %d block(s). Baseline: %d -> %d chars",
            self.caste_name.value, len(blocks_to_archive), baseline_length, new_length,
        )

        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=0,
            pheromones_written=1,
            output_files=[self.THEORY_BASELINE_FILENAME, self.THEORY_ARCHIVE_FILENAME],
            extra_data={
                "blocks_archived": len(blocks_to_archive),
                "blocks_kept": len(blocks_to_keep),
                "baseline_length_before": baseline_length,
                "baseline_length_after": new_length,
                "archive_path": str(archive_path),
                "pheromone_id": pheromone.id,
            },
        )

    def _extract_consolidation_blocks(self, content: str) -> list[str]:
        """
        Extrahiert alle Consolidation-Blöcke aus der Baseline.
        Gibt eine Liste von Block-Strings zurück, in der Reihenfolge,
        in der sie in der Datei erscheinen (älteste zuerst).
        """
        return self.CONSOLIDATION_BLOCK_PATTERN.findall(content)

    def _get_archive_path(self) -> Path:
        """
        Gibt den Pfad zur theory_archive.md im Archive-Verzeichnis zurück.
        Erstellt das Verzeichnis, falls es nicht existiert.
        """
        archive_dir = self.workspace_path / self.KNOWLEDGE_BASE_DIR_NAME / self.ARCHIVE_DIR_NAME
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir / self.THEORY_ARCHIVE_FILENAME

    def _append_to_archive(self, archive_path: Path, blocks: list[str]) -> None:
        """
        Hängt die zu archivierenden Blöcke an die theory_archive.md an.
        Jeder Block wird mit einem Zeitstempel und einer Überschrift versehen.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Archiv initialisieren, falls es nicht existiert
        if not archive_path.exists():
            archive_path.write_text(
                "# Theory Archive\n\n*(Permanently archived knowledge from the swarm.)*\n",
                encoding="utf-8",
            )

        with archive_path.open("a", encoding="utf-8") as f:
            f.write(f"\n## Archived at {timestamp}\n")
            for block in blocks:
                f.write(f"\n{block.strip()}\n")

    def _rewrite_baseline_with_recent_blocks(self, theory_path: Path, original_content: str, recent_blocks: list[str]) -> None:
        """
        Schreibt die aktive Baseline neu, wobei nur die neuesten
        Consolidation-Blöcke behalten werden. Der Rest der Datei
        (Header, etc.) bleibt erhalten.
        """
        # Entferne alle Consolidation-Blöcke aus dem Original
        content_without_blocks = self.CONSOLIDATION_BLOCK_PATTERN.sub("", original_content)
        content_without_blocks = content_without_blocks.rstrip() + "\n"

        # Füge die neuesten Blöcke wieder hinzu
        new_content = content_without_blocks + "\n" + "\n".join(recent_blocks)

        theory_path.write_text(new_content, encoding="utf-8")

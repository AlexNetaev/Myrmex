"""
src/castes/guardian.py
Die GuardianCaste — der Wächter des Wissens.

Validiert die theory_baseline.md (im 04_Knowledge_Base/-Verzeichnis) auf
Plausibilität und strukturelle Integrität. Sie ist die adversariale
Gegeninstanz zur TheoristCaste: Während die TheoristCaste Wissen aufbaut,
prüft der Guardian es kritisch.

In Phase 1 ist die GuardianCaste rein deterministisch (kein LLM). Sie
führt konkrete, nachprüfbare Checks durch:
  1. Existiert die Datei und ist sie nicht leer?
  2. Hat sie eine erkennbare Struktur (Header)?
  3. Ist sie innerhalb einer sinnvollen Größenordnung (nicht zu lang)?
  4. Enthält sie offensichtlich unplausible Muster?

Basierend auf dem Ergebnis schreibt sie:
  - Ein TRAIL-Pheromon mit Tag "validation_passed", wenn alles in Ordnung ist.
  - Ein WARNING-Pheromon mit Tag "validation_failed", wenn Probleme gefunden wurden.

Die GuardianCaste verändert die theory_baseline.md NICHT — sie prüft nur
und meldet. Das Beheben von Problemen ist Aufgabe anderer Kasten oder
einer späteren Phase.
"""
from __future__ import annotations
import logging
import re
from pathlib import Path

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType

logger = logging.getLogger("caste.guardian")


class GuardianCaste(BaseCaste):
    """
    Die GuardianCaste — validiert die theory_baseline.md kritisch.
    """
    
    caste_name = CasteName.GUARDIAN
    role = "Das Langzeitgedächtnis kritisch validieren"
    specialization = "Deterministische Plausibilitäts-Prüfung"
    reads_pheromones = [PheromoneType.TRAIL]
    writes_pheromones = [PheromoneType.TRAIL, PheromoneType.WARNING]
    
    THEORY_BASELINE_FILENAME = "theory_baseline.md"
    KNOWLEDGE_BASE_DIR_NAME = "04_Knowledge_Base"
    
    # Maximale sinnvolle Länge der theory_baseline.md (in Zeichen).
    # Dies ist eine Vorstufe der Token-Hygiene, die später der Archivist
    # übernimmt. Der Guardian meldet nur, er komprimiert nicht.
    MAX_BASELINE_CHARS = 8000
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Validierung aus:
        1. Liest die theory_baseline.md.
        2. Führt deterministische Plausibilitäts-Checks durch.
        3. Schreibt ein Pheromon mit dem Ergebnis (TRAIL oder WARNING).
        """
        self.logger.info("[%s] Starting validation", self.caste_name.value)
        
        # 1. Pfad zur theory_baseline.md bestimmen
        theory_path = self.workspace_path / self.KNOWLEDGE_BASE_DIR_NAME / self.THEORY_BASELINE_FILENAME
        
        # 2. Checks durchführen
        violations = self._run_validation_checks(theory_path)
        
        # 3. Pheromon schreiben (TRAIL wenn ok, WARNING wenn Probleme)
        if violations:
            self.logger.warning(
                "[%s] Validation found %d issue(s): %s",
                self.caste_name.value, len(violations), "; ".join(violations)
            )
            summary = f"Guardian found {len(violations)} issue(s) in theory_baseline.md"
            pheromone = self.write_pheromone(
                pheromone_type=PheromoneType.WARNING,
                content=summary,
                tags=["validation_failed", "theory"],
                strength=0.6,
                relevance=0.7,
            )
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,  # Die Kaste selbst lief erfolgreich, auch wenn sie Probleme fand
                pheromones_read=0,
                pheromones_written=1,
                output_files=[],
                extra_data={
                    "validation_passed": False,
                    "violations": violations,
                    "pheromone_id": pheromone.id,
                },
            )
        else:
            self.logger.info("[%s] Validation passed - theory_baseline.md is plausible", self.caste_name.value)
            summary = "Guardian validated theory_baseline.md - no issues found"
            pheromone = self.write_pheromone(
                pheromone_type=PheromoneType.TRAIL,
                content=summary,
                tags=["validation_passed", "theory"],
                strength=0.4,
                relevance=0.5,
            )
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=1,
                output_files=[],
                extra_data={
                    "validation_passed": True,
                    "violations": [],
                    "pheromone_id": pheromone.id,
                },
            )
    
    def _run_validation_checks(self, theory_path: Path) -> list[str]:
        """
        Führt alle deterministischen Plausibilitäts-Checks durch.
        Gibt eine Liste von Verletzungen zurück (leer = alles in Ordnung).
        """
        violations: list[str] = []
        
        # Check 1: Existiert die Datei?
        if not theory_path.exists():
            violations.append(f"theory_baseline.md does not exist at {theory_path}")
            return violations  # Weitere Checks sind sinnlos ohne Datei
        
        # Check 2: Ist die Datei nicht leer?
        content = theory_path.read_text(encoding="utf-8")
        if not content.strip():
            violations.append("theory_baseline.md is empty")
            return violations  # Weitere Checks sind sinnlos ohne Inhalt
        
        # Check 3: Hat die Datei eine erkennbare Struktur (mindestens einen Header)?
        if not self._has_header(content):
            violations.append("theory_baseline.md has no recognizable header (no line starting with '#')")
        
        # Check 4: Ist die Datei innerhalb einer sinnvollen Größenordnung?
        if len(content) > self.MAX_BASELINE_CHARS:
            violations.append(
                f"theory_baseline.md is {len(content)} characters, exceeding the "
                f"recommended maximum of {self.MAX_BASELINE_CHARS} characters"
            )
        
        # Check 5: Enthält die Datei offensichtlich unplausible Muster?
        implausible_patterns = self._find_implausible_patterns(content)
        violations.extend(implausible_patterns)
        
        return violations
    
    def _has_header(self, content: str) -> bool:
        """Prüft, ob der Inhalt mindestens einen Markdown-Header hat."""
        for line in content.splitlines():
            if line.strip().startswith("#"):
                return True
        return False
    
    def _find_implausible_patterns(self, content: str) -> list[str]:
        """
        Sucht nach offensichtlich unplausiblen Mustern im Inhalt.
        Dies ist eine heuristische, deterministische Prüfung — keine
        vollständige physikalische Validierung.
        """
        violations: list[str] = []
        content_lower = content.lower()
        
        # Muster 1: Temperatur unter absolutem Nullpunkt (-273.15 °C)
        # Suche nach Zahlen, die wie Temperaturen aussehen und unter -273 liegen
        temp_pattern = re.compile(r"-?\d+\.?\d*\s*(?:°c|degrees?\s+celsius|celsius)", re.IGNORECASE)
        for match in temp_pattern.finditer(content_lower):
            try:
                value = float(re.match(r"-?\d+\.?\d*", match.group()).group())
                if value < -273.15:
                    violations.append(
                        f"Implausible temperature value {value}°C (below absolute zero)"
                    )
            except (ValueError, AttributeError):
                continue
        
        # Muster 2: Effizienz oder Ausbeute über 100%
        # Suche sowohl "150% efficiency" als auch "efficiency is 150%"
        efficiency_pattern_after = re.compile(r"(\d+\.?\d*)\s*%\s*(?:efficiency|yield|ausbeute|wirkungsgrad)", re.IGNORECASE)
        efficiency_pattern_before = re.compile(r"(?:efficiency|yield|ausbeute|wirkungsgrad).*?(\d+\.?\d*)\s*%", re.IGNORECASE)
        
        for match in efficiency_pattern_after.finditer(content_lower):
            try:
                value = float(match.group(1))
                if value > 100.0:
                    violations.append(
                        f"Implausible efficiency/yield value {value}% (above 100%)"
                    )
            except (ValueError, AttributeError):
                continue
        
        for match in efficiency_pattern_before.finditer(content_lower):
            try:
                value = float(match.group(1))
                if value > 100.0:
                    violations.append(
                        f"Implausible efficiency/yield value {value}% (above 100%)"
                    )
            except (ValueError, AttributeError):
                continue
        
        # Muster 3: Negative Konzentrationen
        conc_pattern = re.compile(r"-?\d+\.?\d*\s*(?:mm|mmol|mol/l|molar)", re.IGNORECASE)
        for match in conc_pattern.finditer(content_lower):
            # Nur negative Werte melden
            try:
                value = float(re.match(r"-?\d+\.?\d*", match.group()).group())
                if value < 0:
                    violations.append(
                        f"Negative concentration value detected: {match.group()}"
                    )
            except (ValueError, AttributeError):
                continue
        
        return violations

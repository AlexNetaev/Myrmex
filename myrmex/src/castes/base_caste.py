"""
src/castes/base_caste.py
Abstrakte Basisklasse für alle 9 Kasten von Myrmex.

Die Kasten sind die "Arbeiter" des Schwarms. Sie:
- Lesen Pheromone aus dem Feld
- Verarbeiten diese (in Phase 1 nur Platzhalter-Logik)
- Schreiben neue Pheromone ins Feld
- Schreiben Shadow Memory für den Audit-Trail

Der Arbiter (src/arbiter/) ist bewusst KEINE Kaste — er ist eine 
Orchestrierungs-Komponente, nicht ein Arbeiter. Er koordiniert, 
aber "arbeitet" nicht im selben Sinne.
"""
from __future__ import annotations
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
import config

from src.models.caste import CasteName, CasteDefinition, CasteExecutionResult
from src.models.pheromone import Pheromone, PheromoneType
from src.pheromones.pheromone_field import PheromoneField


class BaseCaste(ABC):
    """
    Abstrakte Basisklasse für alle Kasten.
    
    Subklassen MÜSSEN implementieren:
        - caste_name: CasteName (Klassenattribut)
        - role: str (Klassenattribut)
        - specialization: str (Klassenattribut)
        - reads_pheromones: list[PheromoneType] (Klassenattribut)
        - writes_pheromones: list[PheromoneType] (Klassenattribut)
        - execute(work_dir: Path) -> CasteExecutionResult (Methode)
    """
    
    # Von Subklassen zu überschreibende Klassenattribute
    caste_name: CasteName
    role: str
    specialization: str
    reads_pheromones: list[PheromoneType] = []
    writes_pheromones: list[PheromoneType] = []
    
    def __init__(self, workspace_path: Path | None = None) -> None:
        """
        Initialisiert die Kaste.
        
        Args:
            workspace_path: Workspace-Root. Defaults to config.WORKSPACE_ROOT.
        """
        self.workspace_path: Path = (workspace_path or config.WORKSPACE_ROOT).resolve()
        self.pheromone_field = PheromoneField(field_root=self.workspace_path / "01_Pheromon_Field")
        self.logger = logging.getLogger(f"caste.{self.caste_name.value}")
    
    # ------------------------------------------------------------------ #
    # Öffentliche API — wird vom LoopRunner aufgerufen
    # ------------------------------------------------------------------ #
    
    def run(self, work_dir: Path) -> "CasteExecutionResult":
        """
        Führt die Kaste aus. Wrapper um execute() mit Logging und Shadow Memory.
        
        Args:
            work_dir: Das Arbeitsverzeichnis für diese Ausführung
                      (z.B. 02_Research_Cycles/Cycle_001/C_Analysis/)
        
        Returns:
            CasteExecutionResult mit den Ergebnissen der Ausführung.
        """
        self.logger.info(
            "[%s] Starting | work_dir=%s",
            self.caste_name.value, work_dir.name if work_dir else "(none)"
        )
        
        # Start-Zeit für Shadow Memory
        started_at = datetime.now(timezone.utc)
        
        exc = None  # Explizit initialisieren für den except-Block
        try:
            result = self.execute(work_dir)
            success = True
            error_message = None
        except Exception as e:
            exc = e
            self.logger.exception("[%s] Execution failed", self.caste_name.value)
            success = False
            error_message = str(exc)
            # Erzeuge ein "Fehler"-Result, damit Shadow Memory geschrieben werden kann
            result = CasteExecutionResult(
                caste_name=self.caste_name,
                success=False,
                pheromones_written=0,
                pheromones_read=0,
                error_message=error_message,
            )
        
        finished_at = datetime.now(timezone.utc)
        
        # Shadow Memory schreiben (immer, auch bei Fehlern)
        self._write_shadow_memory(
            work_dir=work_dir,
            result=result,
            started_at=started_at,
            finished_at=finished_at,
        )
        
        self.logger.info(
            "[%s] Finished | success=%s | pheromones_read=%d | pheromones_written=%d",
            self.caste_name.value, result.success,
            result.pheromones_read, result.pheromones_written,
        )
        
        if not success and exc is not None:
            raise RuntimeError(
                f"Caste {self.caste_name.value} failed: {error_message}"
            ) from exc
        
        return result
    
    # ------------------------------------------------------------------ #
    # Abstrakte Methode — MUSS von Subklassen implementiert werden
    # ------------------------------------------------------------------ #
    
    @abstractmethod
    def execute(self, work_dir: Path) -> "CasteExecutionResult":
        """
        Führt die eigentliche Arbeit der Kaste aus.
        
        Args:
            work_dir: Das Arbeitsverzeichnis für diese Ausführung.
        
        Returns:
            CasteExecutionResult mit den Ergebnissen.
        
        Subklassen implementieren hier ihre spezifische Logik.
        In Phase 1 sind das meist Platzhalter, die nur Pheromone lesen/schreiben.
        """
        raise NotImplementedError
    
    # ------------------------------------------------------------------ #
    # Helper für Subklassen: Pheromon-Zugriff
    # ------------------------------------------------------------------ #
    
    def read_pheromones(
        self,
        pheromone_type: PheromoneType | None = None,
        min_strength: float | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
    ) -> list[Pheromone]:
        """
        Liest Pheromone aus dem Feld, gefiltert nach Typ/Stärke/Tags.
        
        Nur Pheromon-Typen, die in self.reads_pheromones erlaubt sind,
        können gelesen werden. Andere Typen werden stillschweigend ignoriert.
        
        Args:
            pheromone_type: Nur Pheromone dieses Typs (None = alle erlaubten).
            min_strength: Nur Pheromone mit min. effektiver Stärke.
            tags: Nur Pheromone mit ALLEN diesen Tags.
            limit: Max. Anzahl zurückzugebender Pheromone.
        
        Returns:
            Liste von Pheromonen, sortiert nach effektiver Stärke (absteigend).
        """
        # Validierung: Nur erlaubte Typen lesen
        if pheromone_type is not None and pheromone_type not in self.reads_pheromones:
            self.logger.warning(
                "[%s] Attempted to read pheromone type %s which is not in reads_pheromones. "
                "Returning empty list.",
                self.caste_name.value, pheromone_type.value,
            )
            return []
        
        return self.pheromone_field.scan(
            pheromone_type=pheromone_type,
            min_strength=min_strength,
            tags=tags,
            limit=limit,
        )
    
    def write_pheromone(
        self,
        pheromone_type: PheromoneType,
        content: str,
        tags: list[str] | None = None,
        strength: float = 0.5,
        relevance: float = 0.5,
    ) -> Pheromone:
        """
        Schreibt ein neues Pheromon ins Feld.
        
        Nur Pheromon-Typen, die in self.writes_pheromones erlaubt sind,
        können geschrieben werden.
        
        Args:
            pheromone_type: Typ des Pheromons.
            content: Inhalt des Pheromons.
            tags: Tags zur Kategorisierung.
            strength: Anfangs-Stärke (0.0-1.0, default 0.5).
            relevance: Relevanz für das aktuelle Ziel (0.0-1.0, default 0.5).
        
        Returns:
            Das geschriebene Pheromon (mit generierter ID).
        
        Raises:
            ValueError: Wenn der Typ nicht in writes_pheromones ist.
        """
        if pheromone_type not in self.writes_pheromones:
            raise ValueError(
                f"Caste {self.caste_name.value} is not allowed to write "
                f"pheromone type {pheromone_type.value}. Allowed: "
                f"{[t.value for t in self.writes_pheromones]}"
            )
        
        # ID wird von emit() generiert, wenn leer
        pheromone = Pheromone(
            id=f"pending_{pheromone_type.value}",  # Platzhalter-ID, wird von emit() ersetzt
            type=pheromone_type,
            strength=strength,
            age_cycles=0,
            relevance=relevance,
            content=content,
            tags=tags or [],
            source_agent=self.caste_name.value,
        )
        
        self.pheromone_field.emit(pheromone)
        # Nach emit() hat das Pheromon eine echte ID
        return self.pheromone_field.get(pheromone.id) or pheromone
    
    def reinforce_pheromone(self, pheromone_id: str) -> Pheromone | None:
        """
        Verstärkt ein bestehendes Pheromon (bei Nutzung).
        """
        return self.pheromone_field.reinforce(pheromone_id)
    
    def weaken_pheromone(self, pheromone_id: str) -> Pheromone | None:
        """
        Schwächt ein Pheromon ab (bei Widerlegung).
        """
        return self.pheromone_field.weaken(pheromone_id)
    
    # ------------------------------------------------------------------ #
    # Helper: Kontext-Dateien lesen
    # ------------------------------------------------------------------ #
    
    def read_directive(self) -> str:
        """Liest die aktuelle directive.md."""
        directive_path = self.workspace_path / "00_System" / "directive.md"
        if not directive_path.exists():
            return "(No directive set)"
        text = directive_path.read_text(encoding="utf-8").strip()
        return text if text else "(No directive set)"
    
    def read_theory_baseline(self) -> str:
        """Liest die aktuelle theory_baseline.md."""
        theory_path = self.workspace_path / "04_Knowledge_Base" / "theory_baseline.md"
        if not theory_path.exists():
            return "(No theory baseline yet)"
        text = theory_path.read_text(encoding="utf-8").strip()
        return text if text else "(No theory baseline yet)"
    
    def read_experiment_profile(self) -> dict[str, Any]:
        """Liest das experiment_profile.yaml als dict."""
        # Hinweis: YAML-Parser wird erst später eingebunden, hier nur JSON-Fallback
        profile_path = self.workspace_path / "00_System" / "experiment_profile.yaml"
        if not profile_path.exists():
            return {}
        # Für Phase 1: Nur existence check, kein YAML-Parsing
        return {"_path": str(profile_path), "_exists": True}

    def ask_llm(
        self,
        prompt: str,
        system_prompt: str = "",
        response_model: type | None = None,
        max_retries: int = 3,
        temperature: float = 0.2,
        context_size: int = 4096,
        model: str = "gemma4:31b-cloud",
    ) -> Any:
        """
        Ruft das LLM auf und gibt das validierte Ergebnis zurück.
        
        Args:
            prompt: Der User-Prompt.
            system_prompt: Der System-Prompt.
            response_model: Das Pydantic-Modell für die Validierung.
            max_retries: Maximale Anzahl der Versuche.
            temperature: Die Temperatur für die Generierung.
            context_size: Die Context-Size für das LLM.
            model: Das zu verwendende Modell.
        
        Returns:
            Das validierte Ergebnis (Instanz von response_model).
        
        Raises:
            Exception: Wenn das LLM nicht verfügbar ist oder keine gültige
                       Antwort gibt.
        """
        from src.llm_wrapper import ask_llm_with_validation
        
        return ask_llm_with_validation(
            prompt=prompt,
            system_prompt=system_prompt,
            response_model=response_model,
            max_retries=max_retries,
            model=model,
            temperature=temperature,
            context_size=context_size,
        )
    
    # ------------------------------------------------------------------ #
    # Shadow Memory (Audit-Trail)
    # ------------------------------------------------------------------ #
    
    def _write_shadow_memory(
        self,
        work_dir: Path,
        result: "CasteExecutionResult",
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        """
        Schreibt den Audit-Trail für diese Kasten-Ausführung.
        
        Liegt in work_dir/shadow_memory/<caste_name>_shadow.json,
        oder im workspace-Root, wenn kein work_dir gegeben ist.
        """
        if work_dir and work_dir.exists():
            shadow_dir = work_dir / "shadow_memory"
        else:
            shadow_dir = self.workspace_path / "00_System" / "shadow_memory"
        
        shadow_dir.mkdir(parents=True, exist_ok=True)
        
        shadow_record = {
            "caste_name": self.caste_name.value,
            "role": self.role,
            "specialization": self.specialization,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
            "result": result.model_dump(),
        }
        
        shadow_path = shadow_dir / f"{self.caste_name.value}_shadow.json"
        shadow_path.write_text(json.dumps(shadow_record, indent=2), encoding="utf-8")
        self.logger.debug("[%s] Wrote shadow memory to %s", self.caste_name.value, shadow_path)
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} caste_name={self.caste_name.value!r}>"

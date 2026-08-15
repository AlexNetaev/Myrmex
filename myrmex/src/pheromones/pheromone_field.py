"""
src/pheromones/pheromone_field.py
Der Pheromon-Feld-Manager: Ablegen, Lesen, Verdunsten von Pheromonen.
"""
from __future__ import annotations
import json
import logging
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from src.models.pheromone import Pheromone, PheromoneType, EvaporationResult
import config

logger = logging.getLogger(__name__)


class IndexEntry(BaseModel):
    """Ein Eintrag im Pheromon-Index."""
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(..., description="ID des Pheromons")
    type: PheromoneType = Field(..., description="Typ des Pheromons")
    strength: float = Field(..., ge=0.0, le=1.0)
    effective_strength: float = Field(..., ge=0.0)
    age_cycles: int = Field(..., ge=0)
    relevance: float = Field(..., ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    source_agent: str = Field(...)
    created_at: datetime = Field(...)
    file_path: str = Field(..., description="Relativer Pfad zur Pheromon-Datei")


class PheromonIndex(BaseModel):
    """Der Index aller Pheromone im Feld."""
    model_config = ConfigDict(extra="forbid")
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_count: int = Field(default=0, ge=0)
    pheromones: list[IndexEntry] = Field(default_factory=list)


class PheromoneField:
    """
    Der Pheromon-Feld-Manager: Verwaltet das Ablegen, Lesen, Verstärken,
    Abschwächen, Kristallisieren und Verdunsten von Pheromonen.
    """
    
    def __init__(self, field_root: Path | None = None) -> None:
        """
        Initialisiert das Pheromon-Feld.
        
        Args:
            field_root: Das Wurzelverzeichnis des Feldes (01_Pheromon_Field/).
                        Defaults to config.PHEROMON_FIELD_DIR.
        
        Erstellt die Unterverzeichnisse trails/, crystals/, warnings/,
        falls sie nicht existieren. Lädt den Index in den Speicher.
        """
        self.field_root: Path = (field_root or config.PHEROMON_FIELD_DIR).resolve()
        
        # Unterverzeichnisse
        self.trails_dir = self.field_root / "trails"
        self.crystals_dir = self.field_root / "crystals"
        self.warnings_dir = self.field_root / "warnings"
        self.index_file = self.field_root / "pheromon_index.json"
        
        # Verzeichnisse erstellen
        self._create_directories()
        
        # Index laden oder rekonstruieren
        self._index: PheromonIndex = self._load_or_rebuild_index()
    
    def _create_directories(self) -> None:
        """Erstellt die Unterverzeichnisse des Feldes."""
        for d in [self.field_root, self.trails_dir, self.crystals_dir, self.warnings_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _get_subdir_for_type(self, pheromone_type: PheromoneType) -> Path:
        """Gibt das richtige Unterverzeichnis für einen Pheromon-Typ zurück."""
        if pheromone_type == PheromoneType.TRAIL:
            return self.trails_dir
        elif pheromone_type == PheromoneType.CRYSTAL:
            return self.crystals_dir
        elif pheromone_type == PheromoneType.WARNING:
            return self.warnings_dir
        else:
            raise ValueError(f"Unbekannter Pheromon-Typ: {pheromone_type}")
    
    def _load_or_rebuild_index(self) -> PheromonIndex:
        """Lädt den Index oder重建t ihn aus den Dateien."""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text(encoding="utf-8"))
                index = PheromonIndex.model_validate(data)
                # Validiere, dass alle Einträge existieren
                valid_entries = []
                for entry in index.pheromones:
                    file_path = self.field_root / entry.file_path
                    if file_path.exists():
                        valid_entries.append(entry)
                    else:
                        logger.warning(f"Pheromon-Datei fehlt: {file_path}")
                
                if len(valid_entries) != len(index.pheromones):
                    index.pheromones = valid_entries
                    index.total_count = len(valid_entries)
                    self._save_index(index)
                
                return index
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Index ist korrupt ({e}), wird neu aufgebaut.")
                return self._rebuild_index()
        else:
            logger.info("Index fehlt, wird neu aufgebaut.")
            return self._rebuild_index()
    
    def _rebuild_index(self) -> PheromonIndex:
        """Baut den Index aus allen Pheromon-Dateien neu auf."""
        index = PheromonIndex(pheromones=[])
        
        for subdir, ptype in [
            (self.trails_dir, PheromoneType.TRAIL),
            (self.crystals_dir, PheromoneType.CRYSTAL),
            (self.warnings_dir, PheromoneType.WARNING),
        ]:
            if not subdir.exists():
                continue
            
            for file_path in subdir.glob("*.json"):
                try:
                    pheromone = self._read_pheromone_file(file_path)
                    if pheromone and pheromone.type == ptype:
                        entry = self._create_index_entry(pheromone, file_path)
                        index.pheromones.append(entry)
                except Exception as e:
                    logger.warning(f"Korrupte Pheromon-Datei {file_path}: {e}")
        
        index.total_count = len(index.pheromones)
        index.last_updated = datetime.now(timezone.utc)
        self._save_index(index)
        return index
    
    def _read_pheromone_file(self, file_path: Path) -> Pheromone | None:
        """Liest eine Pheromon-Datei."""
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return Pheromone.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Fehler beim Lesen von {file_path}: {e}")
            return None
    
    def _create_index_entry(self, pheromone: Pheromone, file_path: Path) -> IndexEntry:
        """Erstellt einen Index-Eintrag aus einem Pheromon."""
        rel_path = str(file_path.relative_to(self.field_root))
        return IndexEntry(
            id=pheromone.id,
            type=pheromone.type,
            strength=pheromone.strength,
            effective_strength=pheromone.effective_strength(),
            age_cycles=pheromone.age_cycles,
            relevance=pheromone.relevance,
            tags=pheromone.tags,
            source_agent=pheromone.source_agent,
            created_at=pheromone.created_at,
            file_path=rel_path,
        )
    
    def _save_index(self, index: PheromonIndex) -> None:
        """Speichert den Index atomar."""
        self._atomic_write(self.index_file, index.model_dump(mode="json"))
        self._index = index
    
    def _atomic_write(self, file_path: Path, data: dict[str, Any]) -> None:
        """Schreibt Daten atomar (erst temp-Datei, dann umbenennen)."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Temp-Datei im selben Verzeichnis erstellen
        fd, temp_path = tempfile.mkstemp(suffix=".tmp", dir=file_path.parent)
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomares Umbenennen (funktioniert auf Linux UND Windows)
            Path(temp_path).replace(file_path)
        except Exception:
            # Bei Fehler temp-Datei löschen
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            raise
    
    def _save_pheromone(self, pheromone: Pheromone) -> None:
        """Speichert ein Pheromon atomar in die richtige Datei."""
        subdir = self._get_subdir_for_type(pheromone.type)
        file_path = subdir / f"{pheromone.id}.json"
        self._atomic_write(file_path, pheromone.model_dump(mode="json"))
    
    def _delete_pheromone_file(self, pheromone_id: str, pheromone_type: PheromoneType) -> None:
        """Löscht eine Pheromon-Datei."""
        subdir = self._get_subdir_for_type(pheromone_type)
        file_path = subdir / f"{pheromone_id}.json"
        if file_path.exists():
            file_path.unlink()
    
    def _update_index_for_pheromone(self, pheromone: Pheromone, remove: bool = False) -> None:
        """Aktualisiert den Index für ein Pheromon."""
        # Entferne alten Eintrag falls vorhanden
        self._index.pheromones = [
            e for e in self._index.pheromones if e.id != pheromone.id
        ]
        
        if not remove:
            # Füge neuen Eintrag hinzu
            subdir = self._get_subdir_for_type(pheromone.type)
            file_path = subdir / f"{pheromone.id}.json"
            entry = self._create_index_entry(pheromone, file_path)
            self._index.pheromones.append(entry)
        
        self._index.total_count = len(self._index.pheromones)
        self._index.last_updated = datetime.now(timezone.utc)
        self._save_index(self._index)
    
    def emit(self, pheromone: Pheromone) -> str:
        """
        Legt ein Pheromon im Feld ab und aktualisiert den Index.
        
        Args:
            pheromone: Das abzulegende Pheromon-Objekt.
        
        Returns:
            Die ID des abgelegten Pheromons.
        """
        # ID generieren falls leer
        if not pheromone.id:
            pheromone.id = f"{pheromone.type.value}_{uuid.uuid4().hex[:8]}"
        
        # Pheromon speichern
        self._save_pheromone(pheromone)
        
        # Index aktualisieren
        self._update_index_for_pheromone(pheromone)
        
        logger.debug(f"Pheromon abgelegt: {pheromone.id} ({pheromone.type.value})")
        return pheromone.id
    
    def scan(
        self,
        pheromone_type: PheromoneType | None = None,
        min_strength: float | None = None,
        tags: list[str] | None = None,
        source_agent: str | None = None,
        limit: int | None = None,
    ) -> list[Pheromone]:
        """
        Scannt das Feld und gibt eine Liste von Pheromonen zurück.
        
        Args:
            pheromone_type: Nur Pheromone dieses Typs (None = alle Typen).
            min_strength: Nur Pheromone mit effective_strength() >= diesem Wert.
            tags: Nur Pheromone, die ALLE diese Tags haben.
            source_agent: Nur Pheromone von diesem Agenten.
            limit: Maximale Anzahl zurückzugebender Pheromone.
        
        Returns:
            Liste von Pheromonen, sortiert nach effective_strength() absteigend.
        """
        results: list[Pheromone] = []
        
        for entry in self._index.pheromones:
            # Filter nach Typ
            if pheromone_type is not None and entry.type != pheromone_type:
                continue
            
            # Filter nach Stärke (unter MIN_PHEROMONE_STRENGTH werden ignoriert)
            if entry.effective_strength < config.MIN_PHEROMONE_STRENGTH:
                continue
            
            if min_strength is not None and entry.effective_strength < min_strength:
                continue
            
            # Filter nach Tags (alle müssen vorhanden sein)
            if tags is not None:
                if not all(tag in entry.tags for tag in tags):
                    continue
            
            # Filter nach Quelle
            if source_agent is not None and entry.source_agent != source_agent:
                continue
            
            # Pheromon lesen
            file_path = self.field_root / entry.file_path
            pheromone = self._read_pheromone_file(file_path)
            if pheromone is None:
                continue
            
            results.append(pheromone)
        
        # Sortieren nach effektiver Stärke (absteigend)
        results.sort(key=lambda p: p.effective_strength(), reverse=True)
        
        # Limit anwenden
        if limit is not None:
            results = results[:limit]
        
        return results
    
    def get(self, pheromone_id: str) -> Pheromone | None:
        """
        Gibt ein einzelnes Pheromon anhand seiner ID zurück.
        """
        # Im Index suchen
        entry = next((e for e in self._index.pheromones if e.id == pheromone_id), None)
        if entry is None:
            return None
        
        # Datei lesen
        file_path = self.field_root / entry.file_path
        return self._read_pheromone_file(file_path)
    
    def reinforce(self, pheromone_id: str, amount: float | None = None) -> Pheromone | None:
        """
        Erhöht die Stärke eines Pheromons.
        """
        if amount is None:
            amount = config.REINFORCE_AMOUNT
        
        pheromone = self.get(pheromone_id)
        if pheromone is None:
            return None
        
        # Kristalle werden nicht verstärkt
        if pheromone.type == PheromoneType.CRYSTAL:
            logger.debug(f"Kristall {pheromone_id} wird nicht verstärkt.")
            return pheromone
        
        # Stärke erhöhen, gekappt bei 1.0
        new_strength = min(1.0, pheromone.strength + amount)
        pheromone.strength = new_strength
        
        # Speichern und Index aktualisieren
        self._save_pheromone(pheromone)
        self._update_index_for_pheromone(pheromone)
        
        # Auto-Kristallisierung prüfen
        if pheromone.type == PheromoneType.TRAIL and new_strength >= config.CRYSTALLIZE_THRESHOLD:
            logger.debug(f"Auto-Kristallisierung für {pheromone_id}")
            crystallized = self.crystallize(pheromone_id)
            return crystallized
        
        return pheromone
    
    def weaken(self, pheromone_id: str, amount: float | None = None) -> Pheromone | None:
        """
        Reduziert die Stärke eines Pheromons.
        """
        if amount is None:
            amount = config.WEAKEN_AMOUNT
        
        pheromone = self.get(pheromone_id)
        if pheromone is None:
            return None
        
        # Kristalle können nicht abgeschwächt werden
        if pheromone.type == PheromoneType.CRYSTAL:
            logger.debug(f"Kristall {pheromone_id} kann nicht abgeschwächt werden.")
            return pheromone
        
        # Stärke reduzieren, gekappt bei 0.0
        new_strength = max(0.0, pheromone.strength - amount)
        pheromone.strength = new_strength
        
        # Falls unter MIN_PHEROMONE_STRENGTH, entfernen
        if new_strength < config.MIN_PHEROMONE_STRENGTH:
            logger.debug(f"Pheromon {pheromone_id} wird entfernt (zu schwach).")
            self._delete_pheromone_file(pheromone_id, pheromone.type)
            self._update_index_for_pheromone(pheromone, remove=True)
            return None
        
        # Speichern und Index aktualisieren
        self._save_pheromone(pheromone)
        self._update_index_for_pheromone(pheromone)
        
        return pheromone
    
    def crystallize(self, pheromone_id: str) -> Pheromone | None:
        """
        Wandelt ein TRAIL-Pheromone in ein CRYSTAL-Pheromone um.
        """
        pheromone = self.get(pheromone_id)
        if pheromone is None:
            return None
        
        # Bereits ein Kristall? Idempotent zurückgeben.
        if pheromone.type == PheromoneType.CRYSTAL:
            return pheromone
        
        # Warning kann nicht kristallisiert werden
        if pheromone.type == PheromoneType.WARNING:
            logger.warning(f"Warning {pheromone_id} kann nicht kristallisiert werden.")
            return None
        
        # Typ ändern, Stärke auf 1.0 setzen
        old_type = pheromone.type
        pheromone.type = PheromoneType.CRYSTAL
        pheromone.strength = 1.0
        
        # Alte Datei löschen
        old_subdir = self._get_subdir_for_type(old_type)
        old_file = old_subdir / f"{pheromone_id}.json"
        if old_file.exists():
            old_file.unlink()
        
        # Neue Datei speichern (im crystals/-Verzeichnis)
        self._save_pheromone(pheromone)
        self._update_index_for_pheromone(pheromone)
        
        logger.info(f"Pheromon {pheromone_id} wurde kristallisiert.")
        return pheromone
    
    def evaporate(self) -> EvaporationResult:
        """
        Wendet die Verdunstung auf alle Pheromone im Feld an.
        """
        result = EvaporationResult()
        
        # Gesamtstärke vorher berechnen
        for entry in self._index.pheromones:
            result.total_strength_before += entry.effective_strength
        
        # Alle Pheromone verarbeiten
        pheromones_to_update: list[Pheromone] = []
        pheromones_to_remove: list[tuple[str, PheromoneType]] = []
        
        for entry in self._index.pheromones:
            pheromone = self.get(entry.id)
            if pheromone is None:
                continue
            
            # Alter erhöhen
            pheromone.age_cycles += 1
            
            if pheromone.type == PheromoneType.CRYSTAL:
                result.crystals_unchanged += 1
                # Kristalle verdunsten nie, aber wir speichern trotzdem das neue Alter
                pheromones_to_update.append(pheromone)
            
            elif pheromone.type == PheromoneType.TRAIL:
                # Trail verdunstet mit TRAIL_EVAPORATION_RATE
                new_strength = max(0.0, pheromone.strength - config.TRAIL_EVAPORATION_RATE)
                pheromone.strength = new_strength
                
                if new_strength < config.MIN_PHEROMONE_STRENGTH:
                    pheromones_to_remove.append((pheromone.id, pheromone.type))
                    result.trails_evaporated += 1
                else:
                    pheromones_to_update.append(pheromone)
                    result.trails_remaining += 1
            
            elif pheromone.type == PheromoneType.WARNING:
                # Warning verdunstet mit WARNING_EVAPORATION_RATE
                new_strength = max(0.0, pheromone.strength - config.WARNING_EVAPORATION_RATE)
                pheromone.strength = new_strength
                
                if new_strength < config.MIN_PHEROMONE_STRENGTH:
                    pheromones_to_remove.append((pheromone.id, pheromone.type))
                    result.warnings_evaporated += 1
                else:
                    pheromones_to_update.append(pheromone)
                    result.warnings_remaining += 1
        
        # Pheromone aktualisieren
        for pheromone in pheromones_to_update:
            self._save_pheromone(pheromone)
            self._update_index_for_pheromone(pheromone)
        
        # Pheromone entfernen
        for pheromone_id, ptype in pheromones_to_remove:
            self._delete_pheromone_file(pheromone_id, ptype)
            # Entferne aus Index ohne ein neues Pheromon zu erstellen
            self._index.pheromones = [
                e for e in self._index.pheromones if e.id != pheromone_id
            ]
            self._index.total_count = len(self._index.pheromones)
            self._index.last_updated = datetime.now(timezone.utc)
            self._save_index(self._index)
        
        # Gesamtstärke nachher berechnen
        for entry in self._index.pheromones:
            result.total_strength_after += entry.effective_strength
        
        return result
    
    def auto_crystallize(self, threshold: float | None = None) -> list[str]:
        """
        Kristallisiert automatisch alle TRAIL-Pheromone über dem Schwellenwert.
        """
        if threshold is None:
            threshold = config.CRYSTALLIZE_THRESHOLD
        
        crystallized: list[str] = []
        
        # Alle TRAIL-Pheromone finden
        trails = self.scan(pheromone_type=PheromoneType.TRAIL)
        
        for trail in trails:
            if trail.strength >= threshold:
                self.crystallize(trail.id)
                crystallized.append(trail.id)
        
        return crystallized

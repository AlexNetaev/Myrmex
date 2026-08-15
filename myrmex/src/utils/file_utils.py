"""
src/utils/file_utils.py
Zentrale Helper-Funktionen für Datei-Operationen.
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(file_path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """
    Schreibt JSON-Daten atomar (erst temp-Datei, dann umbenennen).
    Funktioniert auf Linux UND Windows.
    
    Args:
        file_path: Der Pfad zur Zieldatei.
        data: Die zu schreibenden Daten.
        indent: Die Einrückung für das JSON.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Temp-Datei im selben Verzeichnis erstellen
    fd, temp_path = tempfile.mkstemp(suffix=".tmp", dir=file_path.parent)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str)
        
        # Atomares Umbenennen (funktioniert auf Linux UND Windows)
        Path(temp_path).replace(file_path)
    except Exception:
        # Bei Fehler temp-Datei löschen
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Schreibt Text atomar (erst temp-Datei, dann umbenennen).
    Funktioniert auf Linux UND Windows.
    
    Args:
        file_path: Der Pfad zur Zieldatei.
        content: Der zu schreibende Text.
        encoding: Die Kodierung.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Temp-Datei im selben Verzeichnis erstellen
    fd, temp_path = tempfile.mkstemp(suffix=".tmp", dir=file_path.parent)
    try:
        with open(fd, "w", encoding=encoding) as f:
            f.write(content)
        
        # Atomares Umbenennen (funktioniert auf Linux UND Windows)
        Path(temp_path).replace(file_path)
    except Exception:
        # Bei Fehler temp-Datei löschen
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise

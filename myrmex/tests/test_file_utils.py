"""
Tests für die file_utils Helper-Funktionen.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.utils.file_utils import atomic_write_json, atomic_write_text


@pytest.fixture
def temp_dir():
    """Erstellt ein temporäres Verzeichnis."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestAtomicWriteJson:
    """Tests für atomic_write_json."""

    def test_writes_json_file(self, temp_dir):
        """JSON-Datei wird geschrieben."""
        file_path = temp_dir / "test.json"
        data = {"key": "value", "number": 42}
        
        atomic_write_json(file_path, data)
        
        assert file_path.exists()
        import json
        content = json.loads(file_path.read_text(encoding="utf-8"))
        assert content == data

    def test_overwrites_existing_file(self, temp_dir):
        """Bestehende Datei wird überschrieben (Windows-kompatibel)."""
        file_path = temp_dir / "test.json"
        
        # Erste Datei schreiben
        atomic_write_json(file_path, {"version": 1})
        
        # Zweite Datei schreiben (sollte überschreiben)
        atomic_write_json(file_path, {"version": 2})
        
        import json
        content = json.loads(file_path.read_text(encoding="utf-8"))
        assert content == {"version": 2}

    def test_no_temp_file_left(self, temp_dir):
        """Keine temp-Datei bleibt zurück."""
        file_path = temp_dir / "test.json"
        atomic_write_json(file_path, {"key": "value"})
        
        # Keine .tmp Dateien sollten existieren
        tmp_files = list(temp_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_creates_parent_directories(self, temp_dir):
        """Eltern-Verzeichnisse werden erstellt."""
        file_path = temp_dir / "subdir" / "nested" / "test.json"
        atomic_write_json(file_path, {"key": "value"})
        
        assert file_path.exists()


class TestAtomicWriteText:
    """Tests für atomic_write_text."""

    def test_writes_text_file(self, temp_dir):
        """Text-Datei wird geschrieben."""
        file_path = temp_dir / "test.txt"
        content = "Hello, World!"
        
        atomic_write_text(file_path, content)
        
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    def test_overwrites_existing_file(self, temp_dir):
        """Bestehende Datei wird überschrieben (Windows-kompatibel)."""
        file_path = temp_dir / "test.txt"
        
        atomic_write_text(file_path, "Version 1")
        atomic_write_text(file_path, "Version 2")
        
        assert file_path.read_text(encoding="utf-8") == "Version 2"

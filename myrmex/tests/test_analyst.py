"""
tests/test_analyst.py
Tests für die Analyst-Kaste.
"""
from __future__ import annotations
import csv
import json
import pytest
from pathlib import Path

from src.castes.analyst import AnalystCaste
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType, Pheromone


@pytest.fixture
def temp_work_dir(tmp_path: Path) -> Path:
    """Erstellt ein temporäres Arbeitsverzeichnis."""
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


@pytest.fixture
def sample_measurement_csv(temp_work_dir: Path) -> Path:
    """Erstellt eine einfache measurement.csv für Tests."""
    csv_path = temp_work_dir / "measurement.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_ms", "temp_c", "fluorescence_au"])
        # Aufheizphase
        for i in range(50):
            temp = 20.0 + i * 0.5
            fluor = 100.0 - i * 0.5
            writer.writerow([i * 100, temp, fluor])
        # Plateau-Phase
        for i in range(20):
            writer.writerow([(50 + i) * 100, 45.0, 75.0])
    return csv_path


@pytest.fixture
def analyst_caste(tmp_path: Path) -> AnalystCaste:
    """Erstellt eine AnalystCaste mit temporärem Workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    # Pheromon-Feld-Verzeichnis erstellen
    (workspace / "01_Pheromon_Field").mkdir(parents=True, exist_ok=True)
    (workspace / "01_Pheromon_Field" / "trails").mkdir(parents=True, exist_ok=True)
    (workspace / "01_Pheromon_Field" / "crystals").mkdir(parents=True, exist_ok=True)
    (workspace / "01_Pheromon_Field" / "warnings").mkdir(parents=True, exist_ok=True)
    return AnalystCaste(workspace_path=workspace)


# =============================================================================
# Tests für CSV-Erkennung
# =============================================================================

class TestCsvDetection:
    """Tests für die CSV-Erkennungslogik."""
    
    def test_find_csv_files_finds_measurement(self, temp_work_dir: Path, sample_measurement_csv: Path):
        """_find_csv_files() findet measurement.csv."""
        caste = AnalystCaste.__new__(AnalystCaste)
        files = caste._find_csv_files(temp_work_dir)
        assert len(files) >= 1
        assert any(f.name == "measurement.csv" for f in files)
    
    def test_find_csv_files_finds_sim_data(self, temp_work_dir: Path):
        """_find_csv_files() findet sim_data.csv."""
        sim_path = temp_work_dir / "sim_data.csv"
        sim_path.write_text("time,value\n0,1\n", encoding="utf-8")
        
        caste = AnalystCaste.__new__(AnalystCaste)
        files = caste._find_csv_files(temp_work_dir)
        assert any(f.name == "sim_data.csv" for f in files)
    
    def test_find_csv_files_prioritizes_measurement(self, temp_work_dir: Path):
        """_find_csv_files() priorisiert measurement.csv vor anderen."""
        # Andere CSV zuerst erstellen
        other = temp_work_dir / "other.csv"
        other.write_text("a,b\n1,2\n", encoding="utf-8")
        
        # Dann measurement.csv
        measurement = temp_work_dir / "measurement.csv"
        measurement.write_text("time,val\n0,1\n", encoding="utf-8")
        
        caste = AnalystCaste.__new__(AnalystCaste)
        files = caste._find_csv_files(temp_work_dir)
        
        # measurement.csv sollte zuerst kommen
        assert files[0].name == "measurement.csv"
    
    def test_find_csv_files_empty_directory(self, temp_work_dir: Path):
        """_find_csv_files() gibt leere Liste bei leerem Verzeichnis."""
        caste = AnalystCaste.__new__(AnalystCaste)
        files = caste._find_csv_files(temp_work_dir)
        assert files == []
    
    def test_find_csv_files_nonexistent_directory(self, temp_work_dir: Path):
        """_find_csv_files() behandelt nicht-existierendes Verzeichnis."""
        nonexistent = temp_work_dir / "does_not_exist"
        caste = AnalystCaste.__new__(AnalystCaste)
        files = caste._find_csv_files(nonexistent)
        assert files == []


# =============================================================================
# Tests für CSV-Analyse
# =============================================================================

class TestCsvAnalysis:
    """Tests für die CSV-Analyse-Logik."""
    
    def test_analyze_csv_file_valid(self, sample_measurement_csv: Path):
        """_analyze_csv_file() analysiert eine valide CSV."""
        caste = AnalystCaste.__new__(AnalystCaste)
        result = caste._analyze_csv_file(sample_measurement_csv)
        
        assert result["file"] == "measurement.csv"
        assert result["row_count"] == 70  # 50 + 20
        assert "time_ms" in result["headers"]
        assert "temp_c" in result["numeric_columns"]
        assert "fluorescence_au" in result["numeric_columns"]
        assert "column_statistics" in result
    
    def test_analyze_csv_file_empty(self, temp_work_dir: Path):
        """_analyze_csv_file() behandelt leere CSV (0 Rows)."""
        csv_path = temp_work_dir / "empty.csv"
        csv_path.write_text("time,val\n", encoding="utf-8")  # Nur Header
        
        caste = AnalystCaste.__new__(AnalystCaste)
        result = caste._analyze_csv_file(csv_path)
        
        assert result["error"] == "empty_file"
        assert result["row_count"] == 0
    
    def test_analyze_csv_file_corrupt(self, temp_work_dir: Path):
        """_analyze_csv_file() behandelt korrupte CSV (Fehler)."""
        csv_path = temp_work_dir / "corrupt.csv"
        csv_path.write_text("not,valid,csv\n\n\n", encoding="utf-8")
        
        caste = AnalystCaste.__new__(AnalystCaste)
        result = caste._analyze_csv_file(csv_path)
        
        # Sollte entweder Fehler oder leeres Ergebnis zurückgeben
        assert "error" in result or result.get("row_count", 0) == 0
    
    def test_find_numeric_columns(self, temp_work_dir: Path):
        """_find_numeric_columns() erkennt numerische Spalten."""
        csv_path = temp_work_dir / "test.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "value", "label"])
            writer.writerow([1, 2.5, "text"])
            writer.writerow([2, 3.5, "more"])
        
        caste = AnalystCaste.__new__(AnalystCaste)
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = list(rows[0].keys())
        
        numeric = caste._find_numeric_columns(rows, headers)
        assert "time" in numeric
        assert "value" in numeric
        assert "label" not in numeric
    
    def test_compute_statistics(self):
        """_compute_statistics() berechnet korrekte Statistiken."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        caste = AnalystCaste.__new__(AnalystCaste)
        stats = caste._compute_statistics(values)
        
        assert stats["count"] == 5
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == 3.0
        assert stats["median"] == 3.0
        assert stats["auc"] == 15.0  # Summe
    
    def test_detect_plateau_detected(self):
        """_detect_plateau() erkennt Plateau bei konstanten Werten."""
        # Werte mit Plateau am Ende
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        
        caste = AnalystCaste.__new__(AnalystCaste)
        plateau = caste._detect_plateau(values)
        
        assert plateau["detected"] is True
    
    def test_detect_plateau_not_detected(self):
        """_detect_plateau() erkennt kein Plateau bei stark variierenden Werten."""
        # Stark variierende Werte
        values = [1.0, 10.0, 2.0, 9.0, 3.0, 8.0, 4.0, 7.0, 5.0, 6.0, 1.0, 10.0]
        
        caste = AnalystCaste.__new__(AnalystCaste)
        plateau = caste._detect_plateau(values)
        
        assert plateau["detected"] is False
    
    def test_estimate_slope(self):
        """_estimate_slope() berechnet Steigung korrekt."""
        # Lineare Steigung
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        caste = AnalystCaste.__new__(AnalystCaste)
        slope = caste._estimate_slope(values)
        
        # (5 - 1) / 5 = 0.8
        assert abs(slope - 0.8) < 0.01


# =============================================================================
# Tests für vollständige Ausführung
# =============================================================================

class TestExecute:
    """Tests für die vollständige execute()-Methode."""
    
    def test_execute_writes_analysis_json(self, temp_work_dir: Path, sample_measurement_csv: Path, analyst_caste: AnalystCaste):
        """execute() schreibt Analyse-JSON-Dateien."""
        result = analyst_caste.execute(temp_work_dir)
        
        # JSON-Datei sollte existieren
        json_path = temp_work_dir / "measurement_analysis.json"
        assert json_path.exists()
        
        # Inhalt sollte valide JSON sein
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "file" in data
        assert data["file"] == "measurement.csv"
    
    def test_execute_writes_trail_pheromone(self, temp_work_dir: Path, sample_measurement_csv: Path, analyst_caste: AnalystCaste):
        """execute() schreibt ein TRAIL-Pheromon."""
        result = analyst_caste.execute(temp_work_dir)
        
        assert result.pheromones_written == 1
        assert result.success is True
    
    def test_execute_returns_correct_result(self, temp_work_dir: Path, sample_measurement_csv: Path, analyst_caste: AnalystCaste):
        """execute() gibt korrektes CasteExecutionResult zurück."""
        result = analyst_caste.execute(temp_work_dir)
        
        assert result.caste_name == CasteName.ANALYST
        assert result.success is True
        assert result.pheromones_read == 0  # Analyst liest keine Pheromone
        assert result.pheromones_written == 1
        assert "measurement_analysis.json" in result.output_files
        assert "csv_files_analyzed" in result.extra_data
    
    def test_execute_empty_work_dir(self, temp_work_dir: Path, analyst_caste: AnalystCaste):
        """execute() behandelt leeres work_dir gracefully."""
        result = analyst_caste.execute(temp_work_dir)
        
        assert result.success is True
        assert result.pheromones_written == 0
        assert result.extra_data.get("reason") == "no_csv_files_found"
    
    def test_caste_definition(self):
        """Überprüft die Kasten-Definition."""
        assert AnalystCaste.caste_name == CasteName.ANALYST
        assert AnalystCaste.role == "Daten auswerten und Erkenntnisse extrahieren"
        assert AnalystCaste.specialization == "Statistische Analyse von Zeitreihen-Daten"
        assert AnalystCaste.reads_pheromones == []
        assert AnalystCaste.writes_pheromones == [PheromoneType.TRAIL]

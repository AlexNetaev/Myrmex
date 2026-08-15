"""
tests/test_pheromone_field.py
Tests für den Pheromon-Feld-Manager.
"""
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from src.models.pheromone import Pheromone, PheromoneType, EvaporationResult
from src.pheromones.pheromone_field import PheromoneField, IndexEntry, PheromonIndex
import config


@pytest.fixture
def temp_field():
    """Erstellt ein temporäres Pheromon-Feld für Tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        field = PheromoneField(Path(tmpdir))
        yield field


@pytest.fixture
def sample_trail():
    """Erstellt ein Sample-Trail-Pheromon."""
    return Pheromone(
        id="trail_test123",
        type=PheromoneType.TRAIL,
        strength=0.8,
        age_cycles=0,
        relevance=0.9,
        content="Test trail content",
        tags=["test", "kinetics"],
        source_agent="analyst"
    )


@pytest.fixture
def sample_crystal():
    """Erstellt ein Sample-Crystal-Pheromon."""
    return Pheromone(
        id="crystal_test456",
        type=PheromoneType.CRYSTAL,
        strength=1.0,
        age_cycles=5,
        relevance=1.0,
        content="Test crystal content",
        tags=["hard_limit"],
        source_agent="guardian"
    )


@pytest.fixture
def sample_warning():
    """Erstellt ein Sample-Warning-Pheromon."""
    return Pheromone(
        id="warning_test789",
        type=PheromoneType.WARNING,
        strength=0.7,
        age_cycles=2,
        relevance=0.8,
        content="Test warning content",
        tags=["danger"],
        source_agent="guardian"
    )


class TestPheromoneFieldInit:
    """Tests für die Initialisierung des Pheromon-Felds."""
    
    def test_init_creates_directories(self, temp_field):
        """Test, dass alle Verzeichnisse erstellt werden."""
        assert temp_field.trails_dir.exists()
        assert temp_field.crystals_dir.exists()
        assert temp_field.warnings_dir.exists()
        assert temp_field.index_file.exists()
    
    def test_init_with_custom_path(self):
        """Test der Initialisierung mit benutzerdefiniertem Pfad."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_field"
            field = PheromoneField(custom_path)
            assert field.field_root == custom_path
            assert field.trails_dir.exists()


class TestEmit:
    """Tests für die emit()-Methode."""
    
    def test_emit_trail(self, temp_field, sample_trail):
        """Test das Ablegen eines Trail-Pheromons."""
        pid = temp_field.emit(sample_trail)
        assert pid == "trail_test123"
        
        # Datei sollte existieren
        file_path = temp_field.trails_dir / "trail_test123.json"
        assert file_path.exists()
        
        # Index sollte aktualisiert sein
        assert temp_field._index.total_count == 1
    
    def test_emit_crystal(self, temp_field, sample_crystal):
        """Test das Ablegen eines Crystal-Pheromons."""
        pid = temp_field.emit(sample_crystal)
        assert pid == "crystal_test456"
        
        file_path = temp_field.crystals_dir / "crystal_test456.json"
        assert file_path.exists()
    
    def test_emit_warning(self, temp_field, sample_warning):
        """Test das Ablegen eines Warning-Pheromons."""
        pid = temp_field.emit(sample_warning)
        assert pid == "warning_test789"
        
        file_path = temp_field.warnings_dir / "warning_test789.json"
        assert file_path.exists()
    
    def test_emit_generates_id_if_empty(self, temp_field):
        """Test, dass eine ID generiert wird, wenn keine angegeben ist."""
        # Erstelle Pheromon mit None als ID (wird von Pydantic erlaubt)
        p = Pheromone.model_construct(
            id="",  # Leere ID wird generiert
            type=PheromoneType.TRAIL,
            strength=0.5,
            age_cycles=0,
            relevance=1.0,
            content="Auto-ID test",
            source_agent="test"
        )
        pid = temp_field.emit(p)
        assert pid.startswith("trail_")
        assert len(pid) == 14  # "trail_" + 8 hex chars
    
    def test_emit_updates_existing(self, temp_field, sample_trail):
        """Test, dass ein existierendes Pheromon aktualisiert wird."""
        temp_field.emit(sample_trail)
        
        # Ändere Inhalt
        sample_trail.content = "Updated content"
        sample_trail.strength = 0.9
        temp_field.emit(sample_trail)
        
        got = temp_field.get("trail_test123")
        assert got.content == "Updated content"
        assert got.strength == 0.9


class TestScan:
    """Tests für die scan()-Methode."""
    
    def test_scan_all(self, temp_field, sample_trail, sample_crystal, sample_warning):
        """Test das Scannen aller Pheromone."""
        temp_field.emit(sample_trail)
        temp_field.emit(sample_crystal)
        temp_field.emit(sample_warning)
        
        results = temp_field.scan()
        assert len(results) == 3
    
    def test_scan_by_type(self, temp_field, sample_trail, sample_crystal):
        """Test das Filtern nach Typ."""
        temp_field.emit(sample_trail)
        temp_field.emit(sample_crystal)
        
        trails = temp_field.scan(pheromone_type=PheromoneType.TRAIL)
        assert len(trails) == 1
        assert trails[0].type == PheromoneType.TRAIL
    
    def test_scan_by_min_strength(self, temp_field, sample_trail):
        """Test das Filtern nach minimaler Stärke."""
        sample_trail.strength = 0.5
        sample_trail.relevance = 1.0
        temp_field.emit(sample_trail)
        
        # effective_strength = 0.5 * 1.0 * 1.0 = 0.5 (age=0)
        results = temp_field.scan(min_strength=0.4)
        assert len(results) == 1
        
        results = temp_field.scan(min_strength=0.6)
        assert len(results) == 0
    
    def test_scan_by_tags(self, temp_field, sample_trail):
        """Test das Filtern nach Tags."""
        temp_field.emit(sample_trail)
        
        # Alle Tags müssen vorhanden sein
        results = temp_field.scan(tags=["test"])
        assert len(results) == 1
        
        results = temp_field.scan(tags=["test", "kinetics"])
        assert len(results) == 1
        
        results = temp_field.scan(tags=["nonexistent"])
        assert len(results) == 0
    
    def test_scan_by_source_agent(self, temp_field, sample_trail, sample_crystal):
        """Test das Filtern nach Quelle."""
        temp_field.emit(sample_trail)
        temp_field.emit(sample_crystal)
        
        results = temp_field.scan(source_agent="analyst")
        assert len(results) == 1
        assert results[0].source_agent == "analyst"
    
    def test_scan_sorted_by_effective_strength(self, temp_field):
        """Test, dass Ergebnisse nach effektiver Stärke sortiert sind."""
        p1 = Pheromone(
            id="trail_weak",
            type=PheromoneType.TRAIL,
            strength=0.3,
            age_cycles=0,
            relevance=1.0,
            content="Weak",
            source_agent="test"
        )
        p2 = Pheromone(
            id="trail_strong",
            type=PheromoneType.TRAIL,
            strength=0.9,
            age_cycles=0,
            relevance=1.0,
            content="Strong",
            source_agent="test"
        )
        
        temp_field.emit(p1)
        temp_field.emit(p2)
        
        results = temp_field.scan(pheromone_type=PheromoneType.TRAIL)
        assert results[0].id == "trail_strong"
        assert results[1].id == "trail_weak"
    
    def test_scan_limit(self, temp_field):
        """Test das Limitieren der Ergebnisse."""
        for i in range(5):
            p = Pheromone(
                id=f"trail_{i}",
                type=PheromoneType.TRAIL,
                strength=0.5,
                age_cycles=0,
                relevance=1.0,
                content=f"Trail {i}",
                source_agent="test"
            )
            temp_field.emit(p)
        
        results = temp_field.scan(pheromone_type=PheromoneType.TRAIL, limit=3)
        assert len(results) == 3
    
    def test_scan_excludes_below_min_strength(self, temp_field):
        """Test, dass Pheromone unter MIN_PHEROMONE_STRENGTH ausgeschlossen werden."""
        p = Pheromone(
            id="trail_weak",
            type=PheromoneType.TRAIL,
            strength=0.1,
            age_cycles=10,  # Verdunstung: 1.0 - 10*0.05 = 0.5
            relevance=0.5,
            content="Very weak",
            source_agent="test"
        )
        temp_field.emit(p)
        
        # effective_strength = 0.1 * 0.5 * max(0.1, 0.5) = 0.025 < 0.1
        results = temp_field.scan()
        assert len(results) == 0


class TestGet:
    """Tests für die get()-Methode."""
    
    def test_get_existing(self, temp_field, sample_trail):
        """Test das Abrufen eines existierenden Pheromons."""
        temp_field.emit(sample_trail)
        got = temp_field.get("trail_test123")
        assert got is not None
        assert got.id == "trail_test123"
        assert got.content == "Test trail content"
    
    def test_get_nonexistent(self, temp_field):
        """Test das Abrufen eines nicht-existierenden Pheromons."""
        got = temp_field.get("nonexistent")
        assert got is None


class TestReinforce:
    """Tests für die reinforce()-Methode."""
    
    def test_reinforce_trail(self, temp_field, sample_trail):
        """Test das Verstärken eines Trail-Pheromons."""
        sample_trail.strength = 0.5  # Nach reinforce: 0.6 < 0.9, keine Kristallisierung
        temp_field.emit(sample_trail)
        
        reinforced = temp_field.reinforce("trail_test123")
        assert reinforced is not None
        assert abs(reinforced.strength - 0.6) < 0.001  # 0.5 + 0.1 (float precision)
        assert reinforced.type == PheromoneType.TRAIL  # Sollte noch ein Trail sein
    
    def test_reinforce_caps_at_1(self, temp_field, sample_trail):
        """Test, dass die Stärke bei 1.0 gekappt wird."""
        sample_trail.strength = 0.95
        temp_field.emit(sample_trail)
        
        reinforced = temp_field.reinforce("trail_test123")
        assert reinforced.strength == 1.0
    
    def test_reinforce_crystal_unchanged(self, temp_field, sample_crystal):
        """Test, dass Kristalle nicht verstärkt werden."""
        temp_field.emit(sample_crystal)
        
        reinforced = temp_field.reinforce("crystal_test456")
        assert reinforced is not None
        assert reinforced.strength == 1.0  # Unverändert
    
    def test_reinforce_auto_crystallize(self, temp_field):
        """Test die Auto-Kristallisierung bei Überschreiten des Thresholds."""
        p = Pheromone(
            id="trail_near_threshold",
            type=PheromoneType.TRAIL,
            strength=0.85,
            age_cycles=0,
            relevance=1.0,
            content="Near threshold",
            source_agent="test"
        )
        temp_field.emit(p)
        
        # Nach reinforce: 0.85 + 0.1 = 0.95 >= 0.9 -> Kristallisierung
        reinforced = temp_field.reinforce("trail_near_threshold")
        
        # Sollte jetzt ein Kristall sein
        assert reinforced.type == PheromoneType.CRYSTAL
        assert reinforced.strength == 1.0
        
        # Datei sollte im crystals-Verzeichnis sein
        crystal_file = temp_field.crystals_dir / "trail_near_threshold.json"
        assert crystal_file.exists()
        
        # Sollte nicht mehr im trails-Verzeichnis sein
        trail_file = temp_field.trails_dir / "trail_near_threshold.json"
        assert not trail_file.exists()
    
    def test_reinforce_nonexistent(self, temp_field):
        """Test das Verstärken eines nicht-existierenden Pheromons."""
        result = temp_field.reinforce("nonexistent")
        assert result is None


class TestWeaken:
    """Tests für die weaken()-Methode."""
    
    def test_weaken_trail(self, temp_field, sample_trail):
        """Test das Abschwächen eines Trail-Pheromons."""
        temp_field.emit(sample_trail)
        
        weakened = temp_field.weaken("trail_test123")
        assert weakened is not None
        assert abs(weakened.strength - 0.6) < 0.001  # 0.8 - 0.2 (float precision)
    
    def test_weaken_caps_at_0(self, temp_field, sample_trail):
        """Test, dass die Stärke bei 0.0 gekappt wird."""
        sample_trail.strength = 0.25  # Nach weaken: 0.25 - 0.2 = 0.05 < 0.1 -> entfernt
        temp_field.emit(sample_trail)
        
        weakened = temp_field.weaken("trail_test123")
        # Da strength < MIN_PHEROMONE_STRENGTH, wird es entfernt (None zurückgegeben)
        assert weakened is None
    
    def test_weaken_removes_below_threshold(self, temp_field, sample_trail):
        """Test, dass Pheromone unter MIN_PHEROMONE_STRENGTH entfernt werden."""
        sample_trail.strength = 0.15  # Nach weaken: 0.15 - 0.2 = 0.0 < 0.1
        temp_field.emit(sample_trail)
        
        weakened = temp_field.weaken("trail_test123")
        assert weakened is None  # Wurde entfernt
        
        # Datei sollte gelöscht sein
        file_path = temp_field.trails_dir / "trail_test123.json"
        assert not file_path.exists()
    
    def test_weaken_crystal_unchanged(self, temp_field, sample_crystal):
        """Test, dass Kristalle nicht abgeschwächt werden können."""
        temp_field.emit(sample_crystal)
        
        weakened = temp_field.weaken("crystal_test456")
        assert weakened is not None
        assert weakened.strength == 1.0  # Unverändert
    
    def test_weaken_nonexistent(self, temp_field):
        """Test das Abschwächen eines nicht-existierenden Pheromons."""
        result = temp_field.weaken("nonexistent")
        assert result is None


class TestCrystallize:
    """Tests für die crystallize()-Methode."""
    
    def test_crystallize_trail(self, temp_field, sample_trail):
        """Test das Kristallisieren eines Trail-Pheromons."""
        temp_field.emit(sample_trail)
        
        crystal = temp_field.crystallize("trail_test123")
        assert crystal is not None
        assert crystal.type == PheromoneType.CRYSTAL
        assert crystal.strength == 1.0
        
        # Datei sollte im crystals-Verzeichnis sein
        crystal_file = temp_field.crystals_dir / "trail_test123.json"
        assert crystal_file.exists()
        
        # Sollte nicht mehr im trails-Verzeichnis sein
        trail_file = temp_field.trails_dir / "trail_test123.json"
        assert not trail_file.exists()
    
    def test_crystallize_already_crystal(self, temp_field, sample_crystal):
        """Test die Idempotenz bei bereits kristallisierten Pheromonen."""
        temp_field.emit(sample_crystal)
        
        result = temp_field.crystallize("crystal_test456")
        assert result is not None
        assert result.type == PheromoneType.CRYSTAL
    
    def test_crystallize_warning_fails(self, temp_field, sample_warning):
        """Test, dass Warnings nicht kristallisiert werden können."""
        temp_field.emit(sample_warning)
        
        result = temp_field.crystallize("warning_test789")
        assert result is None
    
    def test_crystallize_nonexistent(self, temp_field):
        """Test das Kristallisieren eines nicht-existierenden Pheromons."""
        result = temp_field.crystallize("nonexistent")
        assert result is None


class TestEvaporate:
    """Tests für die evaporate()-Methode."""
    
    def test_evaporate_trail(self, temp_field, sample_trail):
        """Test die Verdunstung von Trail-Pheromonen."""
        sample_trail.strength = 0.5
        temp_field.emit(sample_trail)
        
        result = temp_field.evaporate()
        
        assert result.trails_remaining == 1
        assert result.crystals_unchanged == 0
        
        # Stärke sollte um TRAIL_EVAPORATION_RATE reduziert sein
        got = temp_field.get("trail_test123")
        assert got.age_cycles == 1
        assert got.strength == 0.45  # 0.5 - 0.05
    
    def test_evaporate_warning(self, temp_field, sample_warning):
        """Test die Verdunstung von Warning-Pheromonen."""
        sample_warning.strength = 0.5
        temp_field.emit(sample_warning)
        
        result = temp_field.evaporate()
        
        assert result.warnings_remaining == 1
        
        got = temp_field.get("warning_test789")
        assert got.age_cycles == 3  # War 2, jetzt 3
        assert got.strength == 0.47  # 0.5 - 0.03
    
    def test_evaporate_crystal_unchanged(self, temp_field, sample_crystal):
        """Test, dass Kristalle nicht verdunsten."""
        temp_field.emit(sample_crystal)
        
        result = temp_field.evaporate()
        
        assert result.crystals_unchanged == 1
        assert result.trails_evaporated == 0
        assert result.warnings_evaporated == 0
        
        got = temp_field.get("crystal_test456")
        assert got.age_cycles == 6  # Alter wird erhöht
        assert got.strength == 1.0  # Stärke bleibt 1.0
    
    def test_evaporate_removes_weak_trails(self, temp_field):
        """Test, dass schwache Trails entfernt werden."""
        p = Pheromone(
            id="trail_weak",
            type=PheromoneType.TRAIL,
            strength=0.12,  # Nach Verdunstung: 0.07 < 0.1
            age_cycles=0,
            relevance=1.0,
            content="Weak trail",
            source_agent="test_agent"  # Nicht leer
        )
        temp_field.emit(p)
        
        result = temp_field.evaporate()
        
        assert result.trails_evaporated == 1
        assert temp_field.get("trail_weak") is None
    
    def test_evaporate_total_strength(self, temp_field, sample_trail):
        """Test die Berechnung der Gesamtstärke."""
        temp_field.emit(sample_trail)
        
        result = temp_field.evaporate()
        
        # Vorher: effective_strength = 0.8 * 0.9 * 1.0 = 0.72
        # Nachher: strength=0.75, age=1, evaporation=0.95
        #         effective_strength = 0.75 * 0.9 * 0.95 = 0.64125
        assert result.total_strength_before > 0
        assert result.total_strength_after < result.total_strength_before


class TestAutoCrystallize:
    """Tests für die auto_crystallize()-Methode."""
    
    def test_auto_crystallize_above_threshold(self, temp_field):
        """Test die Auto-Kristallisierung von Pheromonen über dem Threshold."""
        p1 = Pheromone(
            id="trail_strong",
            type=PheromoneType.TRAIL,
            strength=0.95,
            age_cycles=0,
            relevance=1.0,
            content="Strong",
            source_agent="test"
        )
        p2 = Pheromone(
            id="trail_weak",
            type=PheromoneType.TRAIL,
            strength=0.5,
            age_cycles=0,
            relevance=1.0,
            content="Weak",
            source_agent="test"
        )
        
        temp_field.emit(p1)
        temp_field.emit(p2)
        
        crystallized = temp_field.auto_crystallize()
        
        assert len(crystallized) == 1
        assert "trail_strong" in crystallized
        
        # p1 sollte jetzt ein Kristall sein
        crystal = temp_field.get("trail_strong")
        assert crystal.type == PheromoneType.CRYSTAL
        
        # p2 sollte unverändert sein
        trail = temp_field.get("trail_weak")
        assert trail.type == PheromoneType.TRAIL
    
    def test_auto_crystallize_custom_threshold(self, temp_field):
        """Test die Auto-Kristallisierung mit benutzerdefiniertem Threshold."""
        p = Pheromone(
            id="trail_medium",
            type=PheromoneType.TRAIL,
            strength=0.7,
            age_cycles=0,
            relevance=1.0,
            content="Medium",
            source_agent="test"
        )
        temp_field.emit(p)
        
        # Mit Threshold 0.6 sollte es kristallisieren
        crystallized = temp_field.auto_crystallize(threshold=0.6)
        assert len(crystallized) == 1
        
        # Nochmal mit Threshold 0.8 sollte nichts passieren
        crystallized = temp_field.auto_crystallize(threshold=0.8)
        assert len(crystallized) == 0


class TestRobustness:
    """Tests für Robustheit und Edge Cases."""
    
    def test_index_missing_rebuilds(self):
        """Test, dass ein fehlender Index neu aufgebaut wird."""
        with tempfile.TemporaryDirectory() as tmpdir:
            field_root = Path(tmpdir)
            
            # Verzeichnisse erstellen
            (field_root / "trails").mkdir()
            (field_root / "crystals").mkdir()
            (field_root / "warnings").mkdir()
            
            # Pheromon-Datei manuell erstellen
            p = Pheromone(
                id="manual_trail",
                type=PheromoneType.TRAIL,
                strength=0.8,
                age_cycles=0,
                relevance=1.0,
                content="Manual",
                source_agent="test"
            )
            trail_file = field_root / "trails" / "manual_trail.json"
            trail_file.write_text(json.dumps(p.model_dump(mode="json"), default=str))
            
            # Feld initialisieren (Index fehlt)
            field = PheromoneField(field_root)
            
            # Index sollte重建t worden sein
            assert field._index.total_count == 1
            got = field.get("manual_trail")
            assert got is not None
    
    def test_scan_empty_field(self, temp_field):
        """Test das Scannen eines leeren Felds."""
        results = temp_field.scan()
        assert results == []
    
    def test_get_nonexistent_returns_none(self, temp_field):
        """Test, dass get() None zurückgibt für nicht-existierende IDs."""
        result = temp_field.get("does_not_exist")
        assert result is None
    
    def test_reinforce_on_crystal_returns_unchanged(self, temp_field, sample_crystal):
        """Test, dass reinforce() auf Kristallen unverändert zurückgibt."""
        temp_field.emit(sample_crystal)
        result = temp_field.reinforce("crystal_test456")
        assert result.strength == 1.0
    
    def test_crystallize_on_crystal_is_idempotent(self, temp_field, sample_crystal):
        """Test, dass crystallize() auf Kristallen idempotent ist."""
        temp_field.emit(sample_crystal)
        result = temp_field.crystallize("crystal_test456")
        assert result.type == PheromoneType.CRYSTAL


class TestIndexManagement:
    """Tests für die Index-Verwaltung."""
    
    def test_index_updated_on_emit(self, temp_field, sample_trail):
        """Test, dass der Index bei emit() aktualisiert wird."""
        assert temp_field._index.total_count == 0
        
        temp_field.emit(sample_trail)
        
        assert temp_field._index.total_count == 1
        entry = temp_field._index.pheromones[0]
        assert entry.id == "trail_test123"
        assert entry.type == PheromoneType.TRAIL
    
    def test_index_updated_on_remove(self, temp_field, sample_trail):
        """Test, dass der Index bei remove() aktualisiert wird."""
        temp_field.emit(sample_trail)
        assert temp_field._index.total_count == 1
        
        # Weaken bis zur Entfernung
        sample_trail.strength = 0.15
        temp_field.emit(sample_trail)
        temp_field.weaken("trail_test123")
        
        assert temp_field._index.total_count == 0
    
    def test_index_contains_effective_strength(self, temp_field, sample_trail):
        """Test, dass der Index effective_strength enthält."""
        temp_field.emit(sample_trail)
        
        entry = temp_field._index.pheromones[0]
        expected = sample_trail.effective_strength()
        assert entry.effective_strength == expected

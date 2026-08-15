"""
tests/test_landscape.py
Tests für den LandscapeAnalyzer.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.pheromones.pheromone_field import PheromoneField
from src.arbiter.landscape import LandscapeAnalyzer
from src.models.pheromone import Pheromone, PheromoneType
from datetime import datetime, timezone


@pytest.fixture
def temp_field():
    """Erstellt ein temporäres Pheromon-Feld für Tests."""
    temp_dir = tempfile.mkdtemp()
    field_path = Path(temp_dir) / "pheromon_field"
    field_path.mkdir()
    
    field = PheromoneField(field_root=field_path)
    yield field
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestLandscapeAnalyzerEmpty:
    """Tests für eine leere Landschaft."""
    
    def test_empty_landscape_counts(self, temp_field):
        """Leere Landschaft → alle Counts = 0."""
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.trail_count == 0
        assert summary.crystal_count == 0
        assert summary.warning_count == 0
        assert summary.total_count == 0
    
    def test_empty_landscape_is_sparse(self, temp_field):
        """Leere Landschaft → is_sparse=True."""
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.is_sparse is True
    
    def test_empty_landscape_no_strong_trail(self, temp_field):
        """Leere Landschaft → has_strong_trail=False."""
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.has_strong_trail is False
        assert summary.strongest_trail_id is None
    
    def test_empty_landscape_no_warning(self, temp_field):
        """Leere Landschaft → has_warning_nearby=False."""
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.has_warning_nearby is False
        assert summary.strongest_warning_id is None
    
    def test_empty_landscape_strength_metrics(self, temp_field):
        """Leere Landschaft → Stärken = 0."""
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.total_effective_strength == 0.0
        assert summary.average_effective_strength == 0.0
        assert summary.max_effective_strength == 0.0


class TestLandscapeAnalyzerSparse:
    """Tests für eine dünne Landschaft."""
    
    def test_few_trails_is_sparse(self, temp_field):
        """Wenige Trails (< 3) und keine Kristalle → is_sparse=True."""
        # Erstelle 2 Trails
        for i in range(2):
            pheromone = Pheromone(
                id=f"trail_{i}",
                type=PheromoneType.TRAIL,
                strength=0.5,
                age_cycles=0,
                relevance=1.0,
                content=f"Trail {i}",
                source_agent="test",
            )
            temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.trail_count == 2
        assert summary.is_sparse is True
    
    def test_few_crystals_is_sparse(self, temp_field):
        """Wenige Kristalle (< 1) und wenige Trails → is_sparse=True."""
        # Erstelle 1 Kristall
        pheromone = Pheromone(
            id="crystal_0",
            type=PheromoneType.CRYSTAL,
            strength=1.0,
            age_cycles=0,
            relevance=1.0,
            content="Crystal 0",
            source_agent="test",
        )
        temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.crystal_count == 1
        # Mit 0 Trails und 1 Kristall ist es immer noch sparse (trails < 3 AND crystals < 1)
        # Aber hier ist crystals = 1, also nicht sparse aufgrund der Kristalle
        # Die Logik ist: len(trails) < 3 AND len(crystals) < 1
        # Also mit 0 trails und 1 crystal: 0 < 3 AND 1 < 1 = True AND False = False
        assert summary.is_sparse is False


class TestLandscapeAnalyzerDense:
    """Tests für eine dichte Landschaft."""
    
    def test_many_trails_and_crystals_not_sparse(self, temp_field):
        """Viele Trails (>= 3) oder viele Kristalle (>= 1) → is_sparse=False."""
        # Erstelle 3 Trails
        for i in range(3):
            pheromone = Pheromone(
                id=f"trail_{i}",
                type=PheromoneType.TRAIL,
                strength=0.5,
                age_cycles=0,
                relevance=1.0,
                content=f"Trail {i}",
                source_agent="test",
            )
            temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.trail_count == 3
        assert summary.is_sparse is False


class TestLandscapeAnalyzerStrongTrail:
    """Tests für starke Trails."""
    
    def test_strong_trail_detected(self, temp_field):
        """Trail mit effective_strength >= 0.5 → has_strong_trail=True."""
        pheromone = Pheromone(
            id="trail_strong",
            type=PheromoneType.TRAIL,
            strength=0.8,
            age_cycles=0,
            relevance=1.0,
            content="Strong trail",
            source_agent="test",
        )
        temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.has_strong_trail is True
        assert summary.strongest_trail_id == "trail_strong"
    
    def test_weak_trail_not_detected(self, temp_field):
        """Trail mit effective_strength < 0.5 → has_strong_trail=False."""
        pheromone = Pheromone(
            id="trail_weak",
            type=PheromoneType.TRAIL,
            strength=0.3,
            age_cycles=0,
            relevance=1.0,
            content="Weak trail",
            source_agent="test",
        )
        temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.has_strong_trail is False


class TestLandscapeAnalyzerWarning:
    """Tests für Warnungen."""
    
    def test_warning_detected(self, temp_field):
        """Warning mit effective_strength >= 0.3 → has_warning_nearby=True."""
        pheromone = Pheromone(
            id="warning_strong",
            type=PheromoneType.WARNING,
            strength=0.5,
            age_cycles=0,
            relevance=1.0,
            content="Strong warning",
            source_agent="test",
        )
        temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.has_warning_nearby is True
        assert summary.strongest_warning_id == "warning_strong"
    
    def test_weak_warning_not_detected(self, temp_field):
        """Warning mit effective_strength < 0.3 → has_warning_nearby=False."""
        pheromone = Pheromone(
            id="warning_weak",
            type=PheromoneType.WARNING,
            strength=0.2,
            age_cycles=0,
            relevance=1.0,
            content="Weak warning",
            source_agent="test",
        )
        temp_field.emit(pheromone)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.has_warning_nearby is False


class TestLandscapeAnalyzerMixed:
    """Tests für gemischte Landschaften."""
    
    def test_mixed_landscape_all_metrics(self, temp_field):
        """Gemischte Landschaft → alle Metriken korrekt."""
        # Erstelle verschiedene Pheromone
        pheromones = [
            Pheromone(id="trail_1", type=PheromoneType.TRAIL, strength=0.6, age_cycles=0, relevance=1.0, content="T1", source_agent="test"),
            Pheromone(id="trail_2", type=PheromoneType.TRAIL, strength=0.4, age_cycles=0, relevance=1.0, content="T2", source_agent="test"),
            Pheromone(id="crystal_1", type=PheromoneType.CRYSTAL, strength=1.0, age_cycles=0, relevance=1.0, content="C1", source_agent="test"),
            Pheromone(id="warning_1", type=PheromoneType.WARNING, strength=0.4, age_cycles=0, relevance=1.0, content="W1", source_agent="test"),
        ]
        
        for p in pheromones:
            temp_field.emit(p)
        
        analyzer = LandscapeAnalyzer(temp_field)
        summary = analyzer.analyze()
        
        assert summary.trail_count == 2
        assert summary.crystal_count == 1
        assert summary.warning_count == 1
        assert summary.total_count == 4
        assert summary.is_sparse is False  # 2 trails aber >= 1 crystal
        assert summary.has_strong_trail is True  # trail_1 hat 0.6
        assert summary.has_warning_nearby is True  # warning_1 hat 0.4
        assert summary.strongest_trail_id == "trail_1"
        assert summary.strongest_warning_id == "warning_1"

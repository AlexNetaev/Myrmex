"""Tests for Pheromone model."""
import pytest
from datetime import datetime, timezone, timedelta

from src.models.pheromone import Pheromone, PheromoneType


def test_pheromone_creation():
    """Test creating a valid Pheromone."""
    pheromone = Pheromone(
        id="test-001",
        type=PheromoneType.TRAIL,
        strength=0.8,
        age_cycles=0,
        relevance=1.0,
        content="Test trail content",
        tags=["test", "trail"],
        source_agent="hypothesizer"
    )
    assert pheromone.id == "test-001"
    assert pheromone.type == PheromoneType.TRAIL
    assert pheromone.strength == 0.8
    assert pheromone.age_cycles == 0
    assert pheromone.relevance == 1.0


def test_pheromone_strength_validation():
    """Test that strength is validated between 0.0 and 1.0."""
    with pytest.raises(Exception):
        Pheromone(
            id="test-002",
            type=PheromoneType.TRAIL,
            strength=1.5,  # Invalid: > 1.0
            age_cycles=0,
            relevance=1.0,
            content="Invalid strength",
            source_agent="hypothesizer"
        )
    
    with pytest.raises(Exception):
        Pheromone(
            id="test-003",
            type=PheromoneType.TRAIL,
            strength=-0.1,  # Invalid: < 0.0
            age_cycles=0,
            relevance=1.0,
            content="Invalid strength",
            source_agent="hypothesizer"
        )


def test_effective_strength_trail():
    """Test effective_strength for TRAIL pheromones."""
    # Fresh trail (age 0)
    pheromone = Pheromone(
        id="trail-fresh",
        type=PheromoneType.TRAIL,
        strength=1.0,
        age_cycles=0,
        relevance=1.0,
        content="Fresh trail",
        source_agent="hypothesizer"
    )
    # evaporation = max(0.1, 1.0 - 0*0.05) = 1.0
    # effective = 1.0 * 1.0 * 1.0 = 1.0
    assert pheromone.effective_strength() == 1.0
    
    # Old trail (age 10)
    pheromone_old = Pheromone(
        id="trail-old",
        type=PheromoneType.TRAIL,
        strength=1.0,
        age_cycles=10,
        relevance=1.0,
        content="Old trail",
        source_agent="hypothesizer"
    )
    # evaporation = max(0.1, 1.0 - 10*0.05) = max(0.1, 0.5) = 0.5
    # effective = 1.0 * 1.0 * 0.5 = 0.5
    assert pheromone_old.effective_strength() == 0.5
    
    # Very old trail (age 20)
    pheromone_very_old = Pheromone(
        id="trail-very-old",
        type=PheromoneType.TRAIL,
        strength=1.0,
        age_cycles=20,
        relevance=1.0,
        content="Very old trail",
        source_agent="hypothesizer"
    )
    # evaporation = max(0.1, 1.0 - 20*0.05) = max(0.1, 0.0) = 0.1
    # effective = 1.0 * 1.0 * 0.1 = 0.1
    assert pheromone_very_old.effective_strength() == 0.1


def test_effective_strength_crystal():
    """Test effective_strength for CRYSTAL pheromones (never evaporate)."""
    # Fresh crystal
    crystal = Pheromone(
        id="crystal-fresh",
        type=PheromoneType.CRYSTAL,
        strength=1.0,
        age_cycles=0,
        relevance=1.0,
        content="Fresh crystal",
        source_agent="theorist"
    )
    assert crystal.effective_strength() == 1.0
    
    # Old crystal (should still be 1.0 since crystals don't evaporate)
    crystal_old = Pheromone(
        id="crystal-old",
        type=PheromoneType.CRYSTAL,
        strength=1.0,
        age_cycles=100,
        relevance=1.0,
        content="Old crystal",
        source_agent="theorist"
    )
    # evaporation = 1.0 (crystals never evaporate)
    # effective = 1.0 * 1.0 * 1.0 = 1.0
    assert crystal_old.effective_strength() == 1.0


def test_effective_strength_warning():
    """Test effective_strength for WARNING pheromones."""
    # Fresh warning
    warning = Pheromone(
        id="warning-fresh",
        type=PheromoneType.WARNING,
        strength=1.0,
        age_cycles=0,
        relevance=1.0,
        content="Fresh warning",
        source_agent="guardian"
    )
    # evaporation = max(0.2, 1.0 - 0*0.03) = 1.0
    # effective = 1.0 * 1.0 * 1.0 = 1.0
    assert warning.effective_strength() == 1.0
    
    # Old warning (age 10)
    warning_old = Pheromone(
        id="warning-old",
        type=PheromoneType.WARNING,
        strength=1.0,
        age_cycles=10,
        relevance=1.0,
        content="Old warning",
        source_agent="guardian"
    )
    # evaporation = max(0.2, 1.0 - 10*0.03) = max(0.2, 0.7) = 0.7
    # effective = 1.0 * 1.0 * 0.7 = 0.7
    assert warning_old.effective_strength() == 0.7
    
    # Very old warning (age 30)
    warning_very_old = Pheromone(
        id="warning-very-old",
        type=PheromoneType.WARNING,
        strength=1.0,
        age_cycles=30,
        relevance=1.0,
        content="Very old warning",
        source_agent="guardian"
    )
    # evaporation = max(0.2, 1.0 - 30*0.03) = max(0.2, 0.1) = 0.2
    # effective = 1.0 * 1.0 * 0.2 = 0.2
    assert warning_very_old.effective_strength() == 0.2


def test_pheromone_relevance():
    """Test that relevance affects effective strength."""
    pheromone = Pheromone(
        id="test-relevance",
        type=PheromoneType.TRAIL,
        strength=1.0,
        age_cycles=0,
        relevance=0.5,  # Half relevance
        content="Half relevant",
        source_agent="hypothesizer"
    )
    # evaporation = 1.0, relevance = 0.5
    # effective = 1.0 * 0.5 * 1.0 = 0.5
    assert pheromone.effective_strength() == 0.5


def test_pheromone_extra_forbid():
    """Test that extra fields are forbidden."""
    with pytest.raises(Exception):
        Pheromone(
            id="test-extra",
            type=PheromoneType.TRAIL,
            strength=1.0,
            age_cycles=0,
            relevance=1.0,
            content="Test",
            source_agent="hypothesizer",
            extra_field="should fail"  # This should raise an error
        )

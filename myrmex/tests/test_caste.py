"""Tests for Caste models."""
import pytest

from src.models.caste import CasteName, CasteDefinition, CasteRegistry
from src.models.pheromone import PheromoneType


def test_caste_name_enum():
    """Test that all 9 castes are defined."""
    assert CasteName.HYPOTHESIZER.value == "hypothesizer"
    assert CasteName.SIMULATOR.value == "simulator"
    assert CasteName.PLANNER.value == "planner"
    assert CasteName.EXECUTOR.value == "executor"
    assert CasteName.ANALYST.value == "analyst"
    assert CasteName.THEORIST.value == "theorist"
    assert CasteName.GUARDIAN.value == "guardian"
    assert CasteName.ARCHIVIST.value == "archivist"
    assert CasteName.ARBITER.value == "arbiter"


def test_caste_definition_creation():
    """Test creating a valid CasteDefinition."""
    caste = CasteDefinition(
        name=CasteName.HYPOTHESIZER,
        role="Generate hypotheses",
        specialization="Creative hypothesis generation based on existing knowledge",
        reads_pheromones=[PheromoneType.CRYSTAL, PheromoneType.TRAIL],
        writes_pheromones=[PheromoneType.TRAIL]
    )
    assert caste.name == CasteName.HYPOTHESIZER
    assert len(caste.reads_pheromones) == 2
    assert len(caste.writes_pheromones) == 1
    assert PheromoneType.TRAIL in caste.writes_pheromones


def test_caste_definition_defaults():
    """Test default values for CasteDefinition."""
    caste = CasteDefinition(
        name=CasteName.EXECUTOR,
        role="Execute experiments",
        specialization="Hardware control and measurement execution"
    )
    assert caste.reads_pheromones == []
    assert caste.writes_pheromones == []


def test_caste_registry_creation():
    """Test creating a CasteRegistry."""
    registry = CasteRegistry(castes={})
    assert registry.castes == {}


def test_caste_registry_get_default_not_implemented():
    """Test that get_default_registry raises NotImplementedError."""
    registry = CasteRegistry(castes={})
    with pytest.raises(NotImplementedError):
        registry.get_default_registry()


def test_caste_definition_extra_forbid():
    """Test that extra fields are forbidden in CasteDefinition."""
    with pytest.raises(Exception):
        CasteDefinition(
            name=CasteName.HYPOTHESIZER,
            role="Test",
            specialization="Test",
            extra_field="should fail"
        )


def test_caste_registry_extra_forbid():
    """Test that extra fields are forbidden in CasteRegistry."""
    with pytest.raises(Exception):
        CasteRegistry(
            castes={},
            extra_field="should fail"
        )

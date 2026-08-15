"""Tests for Directive and TargetCrystal models."""
import pytest

from src.models.directive import Directive, TargetCrystal


def test_directive_creation():
    """Test creating a valid Directive."""
    directive = Directive(
        title="Optimize Fenton Reaction",
        description="Find optimal conditions for the Fenton reaction to maximize fluorescence.",
        success_criteria=[
            "Fluorescence > 500 AU",
            "Reaction time < 60 seconds"
        ],
        constraints=[
            "Temperature must be between 20-40°C",
            "pH must be between 3-7"
        ]
    )
    assert directive.title == "Optimize Fenton Reaction"
    assert len(directive.success_criteria) == 2
    assert len(directive.constraints) == 2


def test_directive_min_length():
    """Test that title has minimum length."""
    with pytest.raises(Exception):
        Directive(
            title="",  # Invalid: empty string
            description="Valid description"
        )


def test_target_crystal_creation():
    """Test creating a valid TargetCrystal."""
    crystal = TargetCrystal(
        id="target-001",
        description="Optimal Fenton reaction conditions",
        criteria={
            "ph_end_min": 5.0,
            "ph_end_max": 6.0,
            "time_s_max": 30.0,
            "fluorescence_au_min": 500.0
        },
        achieved=False
    )
    assert crystal.id == "target-001"
    assert len(crystal.criteria) == 4
    assert crystal.achieved is False


def test_target_crystal_default_values():
    """Test default values for TargetCrystal."""
    crystal = TargetCrystal(
        id="target-002",
        description="Default values test"
    )
    assert crystal.criteria == {}
    assert crystal.achieved is False


def test_target_crystal_achieved():
    """Test setting achieved flag."""
    crystal = TargetCrystal(
        id="target-003",
        description="Achieved target",
        achieved=True
    )
    assert crystal.achieved is True


def test_directive_extra_forbid():
    """Test that extra fields are forbidden in Directive."""
    with pytest.raises(Exception):
        Directive(
            title="Test",
            description="Test description",
            extra_field="should fail"
        )


def test_target_crystal_extra_forbid():
    """Test that extra fields are forbidden in TargetCrystal."""
    with pytest.raises(Exception):
        TargetCrystal(
            id="test",
            description="Test description",
            extra_field="should fail"
        )

"""Tests for ArbiterPlan model."""
import pytest

from src.models.arbiter import ArbiterActionType, ArbiterPlan
from src.models.loop import LoopName


def test_arbiter_action_type_enum():
    """Test that all Arbiter actions are defined."""
    assert ArbiterActionType.EXPLORE.value == "explore"
    assert ArbiterActionType.FOLLOW_TRAIL.value == "follow_trail"
    assert ArbiterActionType.DETOUR.value == "detour"
    assert ArbiterActionType.CONSOLIDATE.value == "consolidate"


def test_arbiter_plan_creation():
    """Test creating a valid ArbiterPlan."""
    plan = ArbiterPlan(
        directive_summary="Optimize Fenton reaction",
        target_crystal_id="target-001",
        loop_priorities=[LoopName.LOOP_A_SIMULATION, LoopName.LOOP_B_EXPERIMENT],
        next_action=ArbiterActionType.FOLLOW_TRAIL,
        next_action_reasoning="Strong trail detected in simulation space"
    )
    assert plan.directive_summary == "Optimize Fenton reaction"
    assert plan.target_crystal_id == "target-001"
    assert len(plan.loop_priorities) == 2
    assert plan.next_action == ArbiterActionType.FOLLOW_TRAIL
    assert plan.revision_count == 0


def test_arbiter_plan_defaults():
    """Test default values for ArbiterPlan."""
    plan = ArbiterPlan(
        directive_summary="Test directive",
        target_crystal_id="test-crystal"
    )
    assert plan.loop_priorities == []
    assert plan.next_action == ArbiterActionType.EXPLORE
    assert plan.next_action_reasoning == ""
    assert plan.revision_count == 0


def test_arbiter_plan_revision_count_validation():
    """Test that revision_count is non-negative."""
    with pytest.raises(Exception):
        ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            revision_count=-1  # Invalid: < 0
        )


def test_arbiter_plan_extra_forbid():
    """Test that extra fields are forbidden in ArbiterPlan."""
    with pytest.raises(Exception):
        ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            extra_field="should fail"
        )

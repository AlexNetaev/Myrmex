"""Tests for Loop models."""
import pytest

from src.models.loop import LoopName, LoopStatus, LoopState


def test_loop_name_enum():
    """Test that all 4 loops are defined."""
    assert LoopName.LOOP_A_SIMULATION.value == "loop_a_simulation"
    assert LoopName.LOOP_B_EXPERIMENT.value == "loop_b_experiment"
    assert LoopName.LOOP_C_KNOWLEDGE.value == "loop_c_knowledge"
    assert LoopName.LOOP_D_COORDINATION.value == "loop_d_coordination"


def test_loop_status_enum():
    """Test that all loop statuses are defined."""
    assert LoopStatus.ACTIVE.value == "active"
    assert LoopStatus.PAUSED.value == "paused"
    assert LoopStatus.BLOCKED.value == "blocked"
    assert LoopStatus.COMPLETED.value == "completed"


def test_loop_state_creation():
    """Test creating a valid LoopState."""
    state = LoopState(
        loop_name=LoopName.LOOP_A_SIMULATION,
        status=LoopStatus.ACTIVE,
        energy=75.0,
        iteration_count=5
    )
    assert state.loop_name == LoopName.LOOP_A_SIMULATION
    assert state.status == LoopStatus.ACTIVE
    assert state.energy == 75.0
    assert state.iteration_count == 5


def test_loop_state_defaults():
    """Test default values for LoopState."""
    state = LoopState(loop_name=LoopName.LOOP_B_EXPERIMENT)
    assert state.status == LoopStatus.PAUSED
    assert state.energy == 100.0
    assert state.iteration_count == 0


def test_loop_state_energy_validation():
    """Test that energy is validated between 0.0 and 100.0."""
    with pytest.raises(Exception):
        LoopState(
            loop_name=LoopName.LOOP_A_SIMULATION,
            energy=150.0  # Invalid: > 100.0
        )
    
    with pytest.raises(Exception):
        LoopState(
            loop_name=LoopName.LOOP_A_SIMULATION,
            energy=-10.0  # Invalid: < 0.0
        )


def test_loop_state_iteration_count_validation():
    """Test that iteration_count is non-negative."""
    with pytest.raises(Exception):
        LoopState(
            loop_name=LoopName.LOOP_A_SIMULATION,
            iteration_count=-1  # Invalid: < 0
        )


def test_loop_state_extra_forbid():
    """Test that extra fields are forbidden in LoopState."""
    with pytest.raises(Exception):
        LoopState(
            loop_name=LoopName.LOOP_A_SIMULATION,
            extra_field="should fail"
        )

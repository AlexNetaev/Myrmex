"""Tests for ExperimentProfile model."""
import pytest

from src.models.experiment_profile import ReagentDose, ExperimentProfile


def test_reagent_dose_creation():
    """Test creating a valid ReagentDose."""
    dose = ReagentDose(
        reagent_name="H2O2",
        volume_ul=100.0,
        concentration_mm=50.0
    )
    assert dose.reagent_name == "H2O2"
    assert dose.volume_ul == 100.0
    assert dose.concentration_mm == 50.0


def test_reagent_dose_validation():
    """Test validation of ReagentDose fields."""
    with pytest.raises(Exception):
        ReagentDose(
            reagent_name="",  # Invalid: empty string
            volume_ul=100.0,
            concentration_mm=50.0
        )
    
    with pytest.raises(Exception):
        ReagentDose(
            reagent_name="H2O2",
            volume_ul=-10.0,  # Invalid: negative volume
            concentration_mm=50.0
        )
    
    with pytest.raises(Exception):
        ReagentDose(
            reagent_name="H2O2",
            volume_ul=100.0,
            concentration_mm=-5.0  # Invalid: negative concentration
        )


def test_experiment_profile_creation():
    """Test creating a valid ExperimentProfile."""
    profile = ExperimentProfile(
        experiment_type="fenton_fluorescence",
        reagents=[
            ReagentDose(reagent_name="H2O2", volume_ul=100.0, concentration_mm=50.0),
            ReagentDose(reagent_name="FeSO4", volume_ul=50.0, concentration_mm=10.0)
        ],
        parameters={
            "target_temperature_c": 25.0,
            "mixing_speed_rpm": 500.0
        },
        observables=["temp_c", "fluorescence_raw_au"],
        physics_models=["fenton_kinetics", "henderson_hasselbalch"]
    )
    assert profile.experiment_type == "fenton_fluorescence"
    assert len(profile.reagents) == 2
    assert len(profile.parameters) == 2
    assert len(profile.observables) == 2
    assert len(profile.physics_models) == 2


def test_experiment_profile_defaults():
    """Test default values for ExperimentProfile."""
    profile = ExperimentProfile(experiment_type="test_experiment")
    assert profile.reagents == []
    assert profile.parameters == {}
    assert profile.observables == []
    assert profile.physics_models == []


def test_experiment_profile_min_length():
    """Test that experiment_type has minimum length."""
    with pytest.raises(Exception):
        ExperimentProfile(
            experiment_type=""  # Invalid: empty string
        )


def test_experiment_profile_extra_forbid():
    """Test that extra fields are forbidden in ExperimentProfile."""
    with pytest.raises(Exception):
        ExperimentProfile(
            experiment_type="test",
            extra_field="should fail"
        )


def test_reagent_dose_extra_forbid():
    """Test that extra fields are forbidden in ReagentDose."""
    with pytest.raises(Exception):
        ReagentDose(
            reagent_name="H2O2",
            volume_ul=100.0,
            concentration_mm=50.0,
            extra_field="should fail"
        )

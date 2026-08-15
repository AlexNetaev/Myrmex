"""Tests für die OFAT-Logik."""
import pytest
from src.castes.ofat import (
    create_baseline_profile,
    next_ofat_step,
    get_current_parameter_name,
    OFAT_PARAMETER_SEQUENCE,
    _find_parameter_config,
)


class TestCreateBaselineProfile:
    """Tests für create_baseline_profile."""
    
    def test_creates_profile_with_all_parameters(self):
        """Basis-Profil enthält alle Parameter mit Default-Werten."""
        profile = create_baseline_profile()
        assert profile["experiment_type"] == "fenton_fluorescence"
        assert "parameters" in profile
        assert "ofat_state" in profile
        
        for config in OFAT_PARAMETER_SEQUENCE:
            assert config.name in profile["parameters"]
            assert profile["parameters"][config.name] == config.default_value
    
    def test_ofat_state_initialized(self):
        """OFAT-State ist korrekt initialisiert."""
        profile = create_baseline_profile()
        ofat_state = profile["ofat_state"]
        assert ofat_state["current_parameter_index"] == 0
        assert len(ofat_state["parameter_sequence"]) == len(OFAT_PARAMETER_SEQUENCE)
        assert ofat_state["iterations_completed"] == 0


class TestNextOfatStep:
    """Tests für next_ofat_step."""
    
    def test_first_step_increases_first_parameter(self):
        """Erster Schritt erhöht den ersten Parameter."""
        profile = create_baseline_profile()
        first_param_name = OFAT_PARAMETER_SEQUENCE[0].name
        first_param_config = OFAT_PARAMETER_SEQUENCE[0]
        
        new_profile = next_ofat_step(profile)
        
        expected_value = first_param_config.default_value + first_param_config.step
        assert new_profile["parameters"][first_param_name] == expected_value
    
    def test_does_not_mutate_original_profile(self):
        """next_ofat_step mutiert das Original-Profil nicht."""
        profile = create_baseline_profile()
        original_value = profile["parameters"][OFAT_PARAMETER_SEQUENCE[0].name]
        
        _ = next_ofat_step(profile)
        
        assert profile["parameters"][OFAT_PARAMETER_SEQUENCE[0].name] == original_value
    
    def test_parameter_wraps_to_min_and_advances(self):
        """Wenn Parameter max erreicht, wird er auf min zurückgesetzt und nächster Parameter gewählt."""
        profile = create_baseline_profile()
        first_param_name = OFAT_PARAMETER_SEQUENCE[0].name
        first_param_config = OFAT_PARAMETER_SEQUENCE[0]
        
        # Setze den Parameter auf max
        profile["parameters"][first_param_name] = first_param_config.max_value
        
        new_profile = next_ofat_step(profile)
        
        # Parameter sollte auf min zurückgesetzt sein
        assert new_profile["parameters"][first_param_name] == first_param_config.min_value
        # OFAT-State sollte zum nächsten Parameter gewechselt haben
        assert new_profile["ofat_state"]["current_parameter_index"] == 1
        # Iterationszähler sollte inkrementiert sein
        assert new_profile["ofat_state"]["iterations_completed"] == 1
    
    def test_ofat_cycles_through_all_parameters(self):
        """OFAT durchläuft alle Parameter in der Sequenz."""
        profile = create_baseline_profile()
        visited_parameters = set()
        
        # Führe genug Schritte aus, um alle Parameter zu besuchen
        for _ in range(100):
            current_param = get_current_parameter_name(profile)
            visited_parameters.add(current_param)
            profile = next_ofat_step(profile)
        
        # Alle Parameter sollten besucht worden sein
        expected_names = {config.name for config in OFAT_PARAMETER_SEQUENCE}
        assert visited_parameters == expected_names
    
    def test_values_stay_within_bounds(self):
        """Alle Werte bleiben innerhalb [min, max]."""
        profile = create_baseline_profile()
        
        for _ in range(200):
            profile = next_ofat_step(profile)
            for config in OFAT_PARAMETER_SEQUENCE:
                value = profile["parameters"][config.name]
                assert config.min_value <= value <= config.max_value, \
                    f"{config.name}={value} außerhalb [{config.min_value}, {config.max_value}]"


class TestGetCurrentParameterName:
    """Tests für get_current_parameter_name."""
    
    def test_returns_first_parameter_initially(self):
        """Am Anfang wird der erste Parameter zurückgegeben."""
        profile = create_baseline_profile()
        assert get_current_parameter_name(profile) == OFAT_PARAMETER_SEQUENCE[0].name
    
    def test_returns_none_for_invalid_index(self):
        """Bei ungültigem Index wird None zurückgegeben."""
        profile = create_baseline_profile()
        profile["ofat_state"]["current_parameter_index"] = 999
        assert get_current_parameter_name(profile) is None
    
    def test_returns_none_for_missing_ofat_state(self):
        """Bei fehlendem ofat_state wird None zurückgegeben."""
        assert get_current_parameter_name({}) is None


class TestFindParameterConfig:
    """Tests für _find_parameter_config."""
    
    def test_finds_existing_parameter(self):
        """Existierender Parameter wird gefunden."""
        config = _find_parameter_config("ascorbic_acid_concentration_mm")
        assert config is not None
        assert config.name == "ascorbic_acid_concentration_mm"
    
    def test_returns_none_for_unknown_parameter(self):
        """Unbekannter Parameter gibt None zurück."""
        assert _find_parameter_config("unknown_parameter") is None

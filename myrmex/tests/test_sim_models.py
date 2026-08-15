"""Tests für die Simulations-Modelle."""
import pytest
from src.castes import sim_models


class TestSimulateTemperature:
    """Tests für simulate_temperature."""
    
    def test_simulate_temperature_starts_at_ambient(self):
        """Bei t=0 ist die Temperatur = ambient."""
        temp = sim_models.simulate_temperature(0.0, target_temp_c=50.0, ambient_temp_c=22.0)
        assert temp == 22.0
    
    def test_simulate_temperature_approaches_target(self):
        """Temperatur nähert sich dem Ziel über die Zeit."""
        # Nach langer Zeit sollte die Temperatur nahe am Ziel sein
        temp = sim_models.simulate_temperature(100.0, target_temp_c=50.0, ambient_temp_c=22.0, tau_s=10.0)
        assert 49.0 < temp < 51.0  # Sollte sehr nahe an 50 sein
    
    def test_simulate_temperature_increases_over_time(self):
        """Temperatur steigt über die Zeit (wenn target > ambient)."""
        temp_0 = sim_models.simulate_temperature(0.0, target_temp_c=50.0, ambient_temp_c=22.0)
        temp_10 = sim_models.simulate_temperature(10.0, target_temp_c=50.0, ambient_temp_c=22.0)
        temp_20 = sim_models.simulate_temperature(20.0, target_temp_c=50.0, ambient_temp_c=22.0)
        assert temp_0 < temp_10 < temp_20


class TestSimulatePh:
    """Tests für simulate_ph."""
    
    def test_simulate_ph_starts_at_ph_start(self):
        """Bei t=0 ist pH = ph_start."""
        ph = sim_models.simulate_ph(0.0, ph_start=7.4)
        assert ph == 7.4
    
    def test_simulate_ph_decreases_over_time(self):
        """pH sinkt über die Zeit."""
        ph_0 = sim_models.simulate_ph(0.0, ph_start=7.4)
        ph_10 = sim_models.simulate_ph(10.0, ph_start=7.4)
        ph_20 = sim_models.simulate_ph(20.0, ph_start=7.4)
        assert ph_0 > ph_10 > ph_20
    
    def test_simulate_ph_approaches_limit(self):
        """pH nähert sich ph_start - delta_ph."""
        ph = sim_models.simulate_ph(100.0, ph_start=7.4, delta_ph=2.0)
        expected_limit = 7.4 - 2.0  # 5.4
        assert abs(ph - expected_limit) < 0.1


class TestSimulateFluorescence:
    """Tests für simulate_fluorescence."""
    
    def test_simulate_fluorescence_high_at_high_ph(self):
        """Fluoreszenz ist hoch bei pH > pKa."""
        fluor = sim_models.simulate_fluorescence(ph=8.0, pka=6.4)
        assert fluor > 50.0  # Sollte relativ hoch sein
    
    def test_simulate_fluorescence_low_at_low_ph(self):
        """Fluoreszenz ist niedrig bei pH < pKa."""
        fluor = sim_models.simulate_fluorescence(ph=5.0, pka=6.4)
        assert fluor < 20.0  # Sollte relativ niedrig sein
    
    def test_simulate_fluorescence_increases_with_ph(self):
        """Fluoreszenz steigt mit dem pH."""
        fluor_5 = sim_models.simulate_fluorescence(ph=5.0)
        fluor_6 = sim_models.simulate_fluorescence(ph=6.0)
        fluor_7 = sim_models.simulate_fluorescence(ph=7.0)
        fluor_8 = sim_models.simulate_fluorescence(ph=8.0)
        assert fluor_5 < fluor_6 < fluor_7 < fluor_8


class TestGenerateTimeSeries:
    """Tests für generate_time_series."""
    
    def test_generate_time_series_empty_for_zero_duration(self):
        """Leere Liste bei duration=0."""
        series = sim_models.generate_time_series(
            duration_s=0,
            interval_ms=500,
            target_temp_c=37.0,
        )
        assert series == []
    
    def test_generate_time_series_negative_duration(self):
        """Leere Liste bei negativer duration."""
        series = sim_models.generate_time_series(
            duration_s=-10,
            interval_ms=500,
            target_temp_c=37.0,
        )
        assert series == []
    
    def test_generate_time_series_correct_length(self):
        """Die Zeitreihe hat die korrekte Länge."""
        duration_s = 60.0
        interval_ms = 500
        series = sim_models.generate_time_series(
            duration_s=duration_s,
            interval_ms=interval_ms,
            target_temp_c=37.0,
        )
        expected_points = int(duration_s / (interval_ms / 1000.0)) + 1
        assert len(series) == expected_points
    
    def test_generate_time_series_all_fields_present(self):
        """Jeder Punkt hat alle Felder."""
        series = sim_models.generate_time_series(
            duration_s=10.0,
            interval_ms=1000,
            target_temp_c=37.0,
        )
        required_fields = {"time_ms", "temp_c", "ph", "fluorescence_au"}
        for point in series:
            assert set(point.keys()) == required_fields
    
    def test_generate_time_series_values_plausible(self):
        """Die Werte sind physikalisch plausibel."""
        series = sim_models.generate_time_series(
            duration_s=60.0,
            interval_ms=500,
            target_temp_c=37.0,
            ph_start=7.4,
        )
        # Temperatur sollte von ~22 auf ~37 steigen
        assert series[0]["temp_c"] < series[-1]["temp_c"]
        # pH sollte sinken
        assert series[0]["ph"] > series[-1]["ph"]
        # Zeit sollte monoton steigen
        for i in range(1, len(series)):
            assert series[i]["time_ms"] > series[i-1]["time_ms"]

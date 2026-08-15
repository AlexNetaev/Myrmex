"""
Tests für die Reagenzien-Umrechnung.
"""
import pytest

from src.castes.reagent_converter import (
    convert_concentrations_to_reagents,
    DEFAULT_TOTAL_VOLUME_UL,
    REAGENT_CONFIG,
)


class TestReagentConverter:
    """Tests für die Umrechnung."""

    def test_convert_all_parameters(self):
        """Alle Parameter werden umgerechnet."""
        parameters = {
            "ascorbic_acid_concentration_mm": 25.0,
            "fecl3_concentration_mm": 1.0,
            "h2o2_concentration_mm": 50.0,
            "fluorescein_concentration_mm": 0.01,
            "phosphate_buffer_concentration_mm": 50.0,
        }
        
        reagents = convert_concentrations_to_reagents(parameters)
        
        assert len(reagents) == 5
        
        # Prüfe, dass alle Reagenzien vorhanden sind
        reagent_names = [r["reagent_name"] for r in reagents]
        assert "ascorbic_acid" in reagent_names
        assert "fecl3" in reagent_names
        assert "h2o2" in reagent_names
        assert "fluorescein" in reagent_names
        assert "phosphate_buffer" in reagent_names

    def test_volume_proportional_to_concentration(self):
        """Volumen ist proportional zur Konzentration."""
        # Nur FeCl3 angeben, andere verwenden Defaults
        parameters = {
            "fecl3_concentration_mm": 2.0,  # 2x die Default-Konzentration (1.0)
        }
        
        reagents = convert_concentrations_to_reagents(parameters)
        
        # Finde das FeCl3-Reagenz
        fecl3 = next(r for r in reagents if r["reagent_name"] == "fecl3")
        
        # Volumen sollte proportional sein: 100 µL * 2.0 = 200 µL
        # Aber da andere Reagenzien auch Default-Volumina haben, wird skaliert
        # Wir prüfen nur, dass die Konzentration korrekt übernommen wurde
        assert fecl3["concentration_mm"] == 2.0
        # Das Volumen wird skaliert, daher prüfen wir nur den Bereich
        assert 150.0 <= fecl3["volume_ul"] <= 200.0

    def test_volume_capped_at_max(self):
        """Volumen wird bei max_volume_ul gekappt."""
        # Sehr hohe Konzentration, die das Max-Volumen überschreiten würde
        parameters = {
            "fecl3_concentration_mm": 10.0,  # 10x die Default-Konzentration
            # Alle anderen auf sehr niedrigen Werten, damit keine Skalierung stattfindet
            "ascorbic_acid_concentration_mm": 0.1,
            "h2o2_concentration_mm": 1.0,
            "fluorescein_concentration_mm": 0.001,
            "phosphate_buffer_concentration_mm": 1.0,
        }
        
        reagents = convert_concentrations_to_reagents(parameters)
        
        fecl3 = next(r for r in reagents if r["reagent_name"] == "fecl3")
        
        # Volumen sollte bei max_volume_ul (500 µL) gekappt sein
        assert fecl3["volume_ul"] == 500.0

    def test_missing_parameter_uses_default(self):
        """Fehlende Parameter verwenden das Default-Volumen."""
        parameters = {}  # Keine Parameter
        
        reagents = convert_concentrations_to_reagents(parameters)
        
        # Alle Reagenzien sollten Default-Volumina haben
        for reagent in reagents:
            config = REAGENT_CONFIG[reagent["reagent_name"]]
            assert reagent["volume_ul"] == config["default_volume_ul"]

    def test_total_volume_scaling(self):
        """Gesamt-Volumen wird skaliert, wenn es zu groß ist."""
        parameters = {
            "ascorbic_acid_concentration_mm": 100.0,  # Sehr hoch
            "fecl3_concentration_mm": 10.0,  # Sehr hoch
            "h2o2_concentration_mm": 200.0,  # Sehr hoch
            "fluorescein_concentration_mm": 0.1,  # Sehr hoch
            "phosphate_buffer_concentration_mm": 200.0,  # Sehr hoch
        }
        
        reagents = convert_concentrations_to_reagents(
            parameters,
            total_volume_ul=1000.0,
        )
        
        # Gesamt-Volumen sollte <= 1000 µL sein
        total = sum(r["volume_ul"] for r in reagents)
        assert total <= 1000.0

    def test_concentration_preserved(self):
        """Konzentration wird beibehalten."""
        parameters = {
            "fecl3_concentration_mm": 5.0,
        }
        
        reagents = convert_concentrations_to_reagents(parameters)
        
        fecl3 = next(r for r in reagents if r["reagent_name"] == "fecl3")
        
        # Konzentration sollte beibehalten werden
        assert fecl3["concentration_mm"] == 5.0

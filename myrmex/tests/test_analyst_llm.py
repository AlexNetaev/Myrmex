"""
Tests für die LLM-Integration in die AnalystCaste.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

from src.castes.analyst import AnalystCaste
from src.castes.analysis_models import AnalysisModel, AnalysisFinding
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace mit measurement.csv und sim_data.csv."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()

    # Benötigte Verzeichnisse
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    cycle_dir = workspace_path / "02_Research_Cycles" / "Cycle_001"
    (cycle_dir / "A_Simulation").mkdir(parents=True)
    (cycle_dir / "B_Hardware").mkdir(parents=True)

    # Measurement-CSV erstellen (realistische Daten)
    meas_csv = cycle_dir / "B_Hardware" / "measurement.csv"
    meas_csv.write_text(
        "time_ms,temp_c,fluorescence_au\n"
        "0,22.0,95.5\n"
        "1000,24.5,88.2\n"
        "2000,28.3,76.4\n"
        "3000,32.1,62.8\n"
        "4000,35.0,50.1\n"
        "5000,36.8,41.3\n",
        encoding="utf-8",
    )

    # Sim-CSV erstellen (etwas abweichend)
    sim_csv = cycle_dir / "A_Simulation" / "sim_data.csv"
    sim_csv.write_text(
        "time_ms,temp_c,ph,fluorescence_au\n"
        "0,22.0,7.4,95.0\n"
        "1000,25.0,7.1,85.0\n"
        "2000,29.0,6.6,70.0\n"
        "3000,33.0,6.1,55.0\n"
        "4000,35.5,5.7,42.0\n"
        "5000,36.5,5.4,35.0\n",
        encoding="utf-8",
    )

    yield workspace_path, cycle_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


class TestAnalystLLMIntegration:
    """Tests für die LLM-Integration in die AnalystCaste."""

    def test_llm_used_when_available(self, temp_workspace):
        """LLM wird verwendet, wenn verfügbar."""
        workspace_path, cycle_dir = temp_workspace

        mock_result = AnalysisModel(
            summary="Fluorescence decreases 54 a.u., faster than simulation predicted.",
            key_findings=[
                AnalysisFinding(
                    description="Fluorescence drop exceeds simulation by 25%.",
                    category="discrepancy",
                    significance="high",
                ),
            ],
            scientific_interpretation="The Fenton reaction proceeds faster than modeled.",
            recommended_next_steps="Reduce FeCl3 concentration by 20% to slow kinetics.",
            confidence="high",
        )

        with patch.object(AnalystCaste, 'ask_llm', return_value=mock_result):
            analyst = AnalystCaste(workspace_path=workspace_path)
            result = analyst.execute(cycle_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is True
            assert result.extra_data["confidence"] == "high"
            assert result.pheromones_written == 1

    def test_fallback_when_llm_fails(self, temp_workspace):
        """Fallback wird verwendet, wenn LLM fehlschlägt."""
        workspace_path, cycle_dir = temp_workspace

        with patch.object(AnalystCaste, 'ask_llm', side_effect=Exception("LLM unavailable")):
            analyst = AnalystCaste(workspace_path=workspace_path)
            result = analyst.execute(cycle_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is False
            # Der Fallback sollte trotzdem findings generieren
            assert result.extra_data["num_findings"] > 0
            assert result.pheromones_written == 1

    def test_analysis_model_validation(self):
        """Das AnalysisModel validiert korrekt."""
        # Gültiges Modell
        valid = AnalysisModel(
            summary="Test summary",
            key_findings=[
                AnalysisFinding(
                    description="Test finding",
                    category="discrepancy",
                    significance="high",
                ),
            ],
            scientific_interpretation="Test interpretation",
            recommended_next_steps="Test recommendation",
            confidence="high",
        )
        assert valid.confidence == "high"
        assert len(valid.key_findings) == 1

    def test_statistics_computation(self, temp_workspace):
        """Statistiken werden korrekt berechnet."""
        workspace_path, cycle_dir = temp_workspace
        analyst = AnalystCaste(workspace_path=workspace_path)

        measurement = analyst._load_csv(cycle_dir / "B_Hardware" / "measurement.csv")
        simulation = analyst._load_csv(cycle_dir / "A_Simulation" / "sim_data.csv")
        stats = analyst._compute_statistics(measurement, simulation)

        assert stats["measurement_points"] == 6
        assert stats["simulation_points"] == 6
        assert stats["has_simulation"] is True
        assert "meas_fluor_delta" in stats
        assert "discrepancy_percent" in stats

    def test_deterministic_fallback_finds_discrepancy(self, temp_workspace):
        """Der Fallback erkennt Diskrepanzen."""
        workspace_path, cycle_dir = temp_workspace
        analyst = AnalystCaste(workspace_path=workspace_path)

        measurement = analyst._load_csv(cycle_dir / "B_Hardware" / "measurement.csv")
        simulation = analyst._load_csv(cycle_dir / "A_Simulation" / "sim_data.csv")
        stats = analyst._compute_statistics(measurement, simulation)
        analysis = analyst._analyze_deterministic(measurement, simulation, stats)

        assert len(analysis["key_findings"]) > 0
        # Mindestens ein Finding sollte ein Trend oder eine Diskrepanz sein
        categories = [f["category"] for f in analysis["key_findings"]]
        assert any(c in categories for c in ["trend", "discrepancy", "confirmation"])

    def test_no_measurement_data_returns_early(self, temp_workspace):
        """Ohne Messdaten wird früh zurückgekehrt."""
        workspace_path, cycle_dir = temp_workspace

        # Measurement-CSV löschen
        meas_csv = cycle_dir / "B_Hardware" / "measurement.csv"
        meas_csv.unlink()

        analyst = AnalystCaste(workspace_path=workspace_path)
        result = analyst.execute(cycle_dir)

        assert result.success is True
        assert result.extra_data["reason"] == "no_measurement_data"
        assert result.pheromones_written == 0

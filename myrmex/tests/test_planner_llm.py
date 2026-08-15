"""
Tests für die LLM-Integration in die PlannerCaste.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch
import yaml

from src.castes.planner import PlannerCaste, VALID_PARAMETERS, PARAMETER_BOUNDS
from src.castes.plan_models import PlanModel, ExperimentStrategy
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType, Pheromone
from src.pheromones.pheromone_field import PheromoneField
from datetime import datetime, timezone


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace mit experiment_profile.yaml."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()

    # Benötigte Verzeichnisse
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "04_Knowledge_Base").mkdir(parents=True)

    # Basis-Profil schreiben
    from src.castes.ofat import create_baseline_profile
    baseline = create_baseline_profile()
    profile_path = workspace_path / "00_System" / "experiment_profile.yaml"
    profile_path.write_text(yaml.dump(baseline), encoding="utf-8")

    yield workspace_path

    shutil.rmtree(temp_dir, ignore_errors=True)


class TestPlannerLLMIntegration:
    """Tests für die LLM-Integration."""

    def test_llm_used_when_available(self, temp_workspace):
        """LLM wird verwendet, wenn verfügbar."""
        mock_result = PlanModel(
            strategy=ExperimentStrategy.OFAT,
            parameter_to_change="target_temperature_c",
            new_value=40.0,
            reasoning="Test reasoning",
            expected_outcome="Test outcome",
            confidence="high",
            summary="Change temp to 40°C",
        )

        with patch.object(PlannerCaste, 'ask_llm', return_value=mock_result):
            planner = PlannerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = planner.execute(work_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is True
            assert result.extra_data["confidence"] == "high"
            assert result.extra_data["parameter_changed"] == "target_temperature_c"
            assert result.extra_data["new_value"] == 40.0

    def test_fallback_when_llm_fails(self, temp_workspace):
        """Fallback wird verwendet, wenn LLM fehlschlägt."""
        with patch.object(PlannerCaste, 'ask_llm', side_effect=Exception("LLM unavailable")):
            planner = PlannerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = planner.execute(work_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is False
            # OFAT-Fallback sollte trotzdem einen Plan generieren
            assert result.extra_data["strategy"] == ExperimentStrategy.OFAT.value
            assert result.pheromones_written == 1

    def test_plan_model_validation(self):
        """Das PlanModel validiert korrekt."""
        valid = PlanModel(
            strategy=ExperimentStrategy.EXPLORATION,
            parameter_to_change="h2o2_concentration_mm",
            new_value=75.0,
            reasoning="Testing H2O2 effect",
            expected_outcome="Faster kinetics",
            confidence="medium",
            summary="Test H2O2 at 75 mM",
        )
        assert valid.strategy == ExperimentStrategy.EXPLORATION
        assert valid.new_value == 75.0

    def test_parameter_bounds_enforced(self, temp_workspace):
        """Parameter-Werte außerhalb der Grenzen werden geclampt."""
        # Wert außerhalb der Grenzen
        mock_result = PlanModel(
            strategy=ExperimentStrategy.OFAT,
            parameter_to_change="target_temperature_c",
            new_value=150.0,  # Über dem Maximum von 80°C
            reasoning="Testing bounds",
            expected_outcome="Hot",
            confidence="low",
            summary="Too hot",
        )

        with patch.object(PlannerCaste, 'ask_llm', return_value=mock_result):
            planner = PlannerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = planner.execute(work_dir)

            # Wert sollte auf Maximum geclampt sein
            assert result.extra_data["new_value"] == 80.0

    def test_experiment_profile_updated(self, temp_workspace):
        """Das experiment_profile.yaml wird korrekt aktualisiert."""
        mock_result = PlanModel(
            strategy=ExperimentStrategy.OFAT,
            parameter_to_change="fecl3_concentration_mm",
            new_value=2.5,
            reasoning="Test FeCl3",
            expected_outcome="More Fe3+",
            confidence="high",
            summary="FeCl3 to 2.5 mM",
        )

        with patch.object(PlannerCaste, 'ask_llm', return_value=mock_result):
            planner = PlannerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            planner.execute(work_dir)

            # Prüfe, ob das Profil aktualisiert wurde
            profile_path = temp_workspace / "00_System" / "experiment_profile.yaml"
            assert profile_path.exists()

            profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            assert profile["parameters"]["fecl3_concentration_mm"] == 2.5

    def test_unknown_parameter_falls_back(self, temp_workspace):
        """Unbekannte Parameter werden auf target_temperature_c zurückgesetzt."""
        mock_result = PlanModel(
            strategy=ExperimentStrategy.OFAT,
            parameter_to_change="unknown_parameter_xyz",
            new_value=42.0,
            reasoning="Test unknown",
            expected_outcome="???",
            confidence="low",
            summary="Unknown param",
        )

        with patch.object(PlannerCaste, 'ask_llm', return_value=mock_result):
            planner = PlannerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = planner.execute(work_dir)

            # Sollte auf target_temperature_c zurückgesetzt sein
            assert result.extra_data["parameter_changed"] == "target_temperature_c"

    def test_all_valid_parameters_accepted(self):
        """Alle gültigen Parameter werden vom PlanModel akzeptiert."""
        for param in VALID_PARAMETERS:
            plan = PlanModel(
                strategy=ExperimentStrategy.OFAT,
                parameter_to_change=param,
                new_value=50.0,
                reasoning="Test",
                expected_outcome="Test",
                confidence="medium",
                summary="Test",
            )
            assert plan.parameter_to_change == param

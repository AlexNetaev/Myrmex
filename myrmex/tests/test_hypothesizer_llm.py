"""
Tests für die LLM-Integration in der HypothesizerCaste.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from src.castes.hypothesizer import HypothesizerCaste
from src.castes.hypothesis_models import HypothesisModel
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType, Pheromone
from src.pheromones.pheromone_field import PheromoneField
from datetime import datetime, timezone


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace für Tests."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()

    # Benötigte Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "04_Knowledge_Base").mkdir(parents=True)

    yield workspace_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def analysis_pheromones(temp_workspace):
    """Erstellt TRAIL-Pheromone mit Analyse-Tags."""
    field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")

    pheromones = []
    for i, (content, tags, source) in enumerate([
        ("Temperature approaches target exponentially", ["analysis"], "analyst"),
        ("Fluorescence decreases with pH drop", ["finding"], "analyst"),
        ("Simulated pH drop matches theory", ["simulation"], "simulator"),
    ]):
        pheromone = Pheromone(
            id=f"test_pheromone_{i}",
            type=PheromoneType.TRAIL,
            content=content,
            tags=tags,
            source_agent=source,
            strength=0.5,
            relevance=0.5,
            age_cycles=0,
        )
        field.emit(pheromone)
        pheromones.append(pheromone)

    return pheromones


class TestHypothesizerLLMIntegration:
    """Tests für die LLM-Integration."""

    def test_llm_used_when_available(self, temp_workspace, analysis_pheromones):
        """LLM wird verwendet, wenn verfügbar."""
        # Mock das LLM
        mock_result = HypothesisModel(
            root_cause_analysis="The pH drop causes fluorescence decrease.",
            proposed_adjustment="Reduce Fluorescein concentration to 5 µM.",
            testable_prediction="Fluorescence should stabilize at lower concentration.",
            confidence="high",
            summary="pH drop causes fluorescence decrease.",
        )

        with patch.object(HypothesizerCaste, 'ask_llm', return_value=mock_result):
            hypothesizer = HypothesizerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = hypothesizer.execute(work_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is True
            assert result.extra_data["confidence"] == "high"

    def test_fallback_when_llm_fails(self, temp_workspace, analysis_pheromones):
        """Fallback wird verwendet, wenn LLM fehlschlägt."""
        # Mock das LLM, um eine Exception zu werfen
        with patch.object(HypothesizerCaste, 'ask_llm', side_effect=Exception("LLM unavailable")):
            hypothesizer = HypothesizerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = hypothesizer.execute(work_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is False
            # Der Fallback sollte trotzdem eine Hypothese generieren
            assert result.pheromones_written == 1

    def test_hypothesis_model_validation(self):
        """Das HypothesisModel validiert korrekt."""
        # Gültiges Modell
        valid = HypothesisModel(
            root_cause_analysis="Test analysis",
            proposed_adjustment="Test adjustment",
            testable_prediction="Test prediction",
            confidence="high",
            summary="Test summary",
        )
        assert valid.confidence == "high"

        # Ungültiges Modell (fehlendes Feld)
        with pytest.raises(Exception):
            HypothesisModel(
                root_cause_analysis="Test analysis",
                # proposed_adjustment fehlt
                testable_prediction="Test prediction",
                confidence="high",
                summary="Test summary",
            )

    def test_hypothesis_file_contains_llm_source(self, temp_workspace, analysis_pheromones):
        """Die hypothesis.md enthält die Quelle (LLM oder Fallback)."""
        mock_result = HypothesisModel(
            root_cause_analysis="The pH drop causes fluorescence decrease.",
            proposed_adjustment="Reduce Fluorescein concentration to 5 µM.",
            testable_prediction="Fluorescence should stabilize at lower concentration.",
            confidence="high",
            summary="pH drop causes fluorescence decrease.",
        )

        with patch.object(HypothesizerCaste, 'ask_llm', return_value=mock_result):
            hypothesizer = HypothesizerCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            hypothesizer.execute(work_dir)

            hypothesis_path = work_dir / "hypothesis.md"
            assert hypothesis_path.exists()
            content = hypothesis_path.read_text(encoding="utf-8")
            assert "gemma4:31b-cloud" in content

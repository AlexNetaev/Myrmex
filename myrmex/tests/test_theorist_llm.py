"""
Tests für die LLM-Integration in die TheoristCaste.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

from src.castes.theorist import TheoristCaste
from src.castes.consolidation_models import ConsolidationModel, ContradictionResolution
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType, Pheromone
from src.pheromones.pheromone_field import PheromoneField
from datetime import datetime, timezone, timedelta


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
def knowledge_pheromones(temp_workspace):
    """Erstellt TRAIL-Pheromone mit Knowledge-Tags."""
    field = PheromoneField(field_root=temp_workspace / "01_Pheromon_Field")

    pheromones = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=2)

    for i, (content, tags, source) in enumerate([
        ("Temperature approaches target exponentially", ["analysis"], "analyst"),
        ("Fluorescence decreases with pH drop", ["finding"], "analyst"),
        ("Simulated pH drop matches theory", ["simulation"], "simulator"),
    ]):
        created_at = base_time + timedelta(minutes=i*10)
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
        pheromone.created_at = created_at
        field.emit(pheromone)
        pheromones.append(pheromone)

    return pheromones


class TestTheoristLLMIntegration:
    """Tests für die LLM-Integration."""

    def test_llm_used_when_available(self, temp_workspace, knowledge_pheromones):
        """LLM wird verwendet, wenn verfügbar."""
        mock_result = ConsolidationModel(
            summary="Consolidated 3 findings about temperature and pH effects.",
            new_knowledge="## Consolidation (2026-08-16T10:00:00Z)\n- Temperature affects reaction kinetics\n- pH drop causes fluorescence decrease",
            contradictions_resolved=[],
            deprecated_knowledge=[],
            confidence="high",
        )

        with patch.object(TheoristCaste, 'ask_llm', return_value=mock_result):
            theorist = TheoristCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = theorist.execute(work_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is True
            assert result.extra_data["confidence"] == "high"
            assert result.pheromones_written == 1

    def test_fallback_when_llm_fails(self, temp_workspace, knowledge_pheromones):
        """Fallback wird verwendet, wenn LLM fehlschlägt."""
        with patch.object(TheoristCaste, 'ask_llm', side_effect=Exception("LLM unavailable")):
            theorist = TheoristCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            result = theorist.execute(work_dir)

            assert result.success is True
            assert result.extra_data["llm_used"] is False
            # Der Fallback sollte trotzdem eine Konsolidierung generieren
            assert result.pheromones_written == 1

    def test_consolidation_model_validation(self):
        """Das ConsolidationModel validiert korrekt."""
        # Gültiges Modell
        valid = ConsolidationModel(
            summary="Test summary",
            new_knowledge="## Consolidation\n- Test finding",
            contradictions_resolved=[],
            deprecated_knowledge=[],
            confidence="high",
        )
        assert valid.confidence == "high"

        # Modell mit Widersprüchen
        with_contradictions = ConsolidationModel(
            summary="Test with contradictions",
            new_knowledge="## Consolidation\n- New finding",
            contradictions_resolved=[
                ContradictionResolution(
                    old_knowledge="Old finding",
                    new_knowledge="New finding",
                    resolution="New finding is correct because...",
                ),
            ],
            deprecated_knowledge=["Old finding"],
            confidence="medium",
        )
        assert len(with_contradictions.contradictions_resolved) == 1
        assert len(with_contradictions.deprecated_knowledge) == 1

    def test_theory_baseline_updated(self, temp_workspace, knowledge_pheromones):
        """Die theory_baseline.md wird aktualisiert."""
        mock_result = ConsolidationModel(
            summary="Test consolidation",
            new_knowledge="## Consolidation (2026-08-16T10:00:00Z)\n- Test finding 1\n- Test finding 2",
            contradictions_resolved=[],
            deprecated_knowledge=[],
            confidence="high",
        )

        with patch.object(TheoristCaste, 'ask_llm', return_value=mock_result):
            theorist = TheoristCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            theorist.execute(work_dir)

            theory_path = temp_workspace / "04_Knowledge_Base" / "theory_baseline.md"
            assert theory_path.exists()
            content = theory_path.read_text(encoding="utf-8")
            assert "Consolidation" in content
            assert "Test finding 1" in content

    def test_contradiction_report_written(self, temp_workspace, knowledge_pheromones):
        """Bei Widersprüchen wird ein separater Bericht geschrieben."""
        mock_result = ConsolidationModel(
            summary="Consolidation with contradictions",
            new_knowledge="## Consolidation\n- New finding",
            contradictions_resolved=[
                ContradictionResolution(
                    old_knowledge="Old: pH has no effect",
                    new_knowledge="New: pH drop decreases fluorescence",
                    resolution="New finding is correct based on experimental evidence",
                ),
            ],
            deprecated_knowledge=["Old: pH has no effect"],
            confidence="medium",
        )

        with patch.object(TheoristCaste, 'ask_llm', return_value=mock_result):
            theorist = TheoristCaste(workspace_path=temp_workspace)
            work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
            work_dir.mkdir(parents=True)

            theorist.execute(work_dir)

            # Contradiction-Report sollte existieren
            contradiction_report_path = temp_workspace / "04_Knowledge_Base" / "contradiction_resolutions.md"
            assert contradiction_report_path.exists()
            content = contradiction_report_path.read_text(encoding="utf-8")
            assert "Contradiction 1" in content
            assert "Resolution" in content

    def test_no_knowledge_pheromones_returns_early(self, temp_workspace):
        """Ohne Knowledge-Pheromone wird früh zurückgekehrt."""
        theorist = TheoristCaste(workspace_path=temp_workspace)
        work_dir = temp_workspace / "02_Research_Cycles" / "Cycle_001"
        work_dir.mkdir(parents=True)

        result = theorist.execute(work_dir)

        assert result.success is True
        assert result.extra_data["reason"] == "no_knowledge_pheromones"
        assert result.pheromones_written == 0

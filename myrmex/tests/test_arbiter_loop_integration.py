"""
tests/test_arbiter_loop_integration.py
Tests für die Arbiter-LoopRunner-Integration.
"""
from __future__ import annotations
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner
from src.models.arbiter import ArbiterActionType, ArbiterCycleResult
from src.models.loop import LoopName


@pytest.fixture
def integration_workspace():
    """Erstellt einen vollständigen temporären Workspace für den Integrationstest."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # Alle benötigten Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    (workspace_path / "02_Research_Cycles").mkdir(parents=True)
    (workspace_path / "03_Hardware_Queue").mkdir(parents=True)
    (workspace_path / "04_Knowledge_Base").mkdir(parents=True)
    (workspace_path / "05_Loops").mkdir(parents=True)
    
    yield workspace_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestArbiterLoopIntegration:
    """Tests für die Integration zwischen Arbiter und LoopRunner."""

    @pytest.fixture
    def arbiter(self, integration_workspace):
        """Erstellt einen Arbiter mit einem Test-Workspace."""
        return Arbiter(workspace_path=integration_workspace)

    @pytest.fixture
    def loop_runner(self, integration_workspace):
        """Erstellt einen LoopRunner mit einem Test-Workspace."""
        return LoopRunner(workspace_path=integration_workspace)

    def test_arbiter_calls_loop_runner(self, arbiter, loop_runner):
        """Der Arbiter ruft den LoopRunner auf."""
        # Mock run_full_loop um zu prüfen, dass es aufgerufen wird
        with patch.object(loop_runner, 'run_full_loop', return_value=[]) as mock_run:
            result = arbiter.run_cycle(loop_runner)
            
            # Prüfen, dass run_full_loop aufgerufen wurde
            assert mock_run.called
            assert isinstance(result, ArbiterCycleResult)

    def test_arbiter_selects_correct_loop_for_explore(self, arbiter, loop_runner):
        """EXPLORE wählt LOOP_B_EXPERIMENT."""
        # Mock decision_engine.decide um EXPLORE zurückzugeben
        with patch.object(arbiter.decision_engine, 'decide', return_value=(ArbiterActionType.EXPLORE, "test", [LoopName.LOOP_B_EXPERIMENT])):
            with patch.object(loop_runner, 'run_full_loop', return_value=[]) as mock_run:
                arbiter.run_cycle(loop_runner)
                
                # Prüfen, dass LOOP_B_EXPERIMENT ausgewählt wurde
                call_args = mock_run.call_args
                assert call_args[0][0] == LoopName.LOOP_B_EXPERIMENT

    def test_arbiter_selects_correct_loop_for_follow_trail(self, arbiter, loop_runner):
        """FOLLOW_TRAIL wählt LOOP_B_EXPERIMENT."""
        with patch.object(arbiter.decision_engine, 'decide', return_value=(ArbiterActionType.FOLLOW_TRAIL, "test", [])):
            with patch.object(loop_runner, 'run_full_loop', return_value=[]) as mock_run:
                arbiter.run_cycle(loop_runner)
                
                call_args = mock_run.call_args
                assert call_args[0][0] == LoopName.LOOP_B_EXPERIMENT

    def test_arbiter_selects_correct_loop_for_detour(self, arbiter, loop_runner):
        """DETOUR wählt LOOP_A_SIMULATION."""
        with patch.object(arbiter.decision_engine, 'decide', return_value=(ArbiterActionType.DETOUR, "test", [])):
            with patch.object(loop_runner, 'run_full_loop', return_value=[]) as mock_run:
                arbiter.run_cycle(loop_runner)
                
                call_args = mock_run.call_args
                assert call_args[0][0] == LoopName.LOOP_A_SIMULATION

    def test_arbiter_selects_correct_loop_for_consolidate(self, arbiter, loop_runner):
        """CONSOLIDATE wählt LOOP_C_KNOWLEDGE."""
        with patch.object(arbiter.decision_engine, 'decide', return_value=(ArbiterActionType.CONSOLIDATE, "test", [])):
            with patch.object(loop_runner, 'run_full_loop', return_value=[]) as mock_run:
                arbiter.run_cycle(loop_runner)
                
                call_args = mock_run.call_args
                assert call_args[0][0] == LoopName.LOOP_C_KNOWLEDGE

    def test_arbiter_cycle_result_contains_loop_results(self, arbiter, loop_runner):
        """Das Ergebnis enthält die Loop-Ergebnisse."""
        mock_results = ["result1", "result2"]
        with patch.object(arbiter.decision_engine, 'decide', return_value=(ArbiterActionType.EXPLORE, "test", [])):
            with patch.object(loop_runner, 'run_full_loop', return_value=mock_results):
                result = arbiter.run_cycle(loop_runner)
                
                assert result.loop_results == mock_results

    def test_arbiter_cycle_result_contains_landscape_summary(self, arbiter, loop_runner):
        """Das Ergebnis enthält die Landschafts-Zusammenfassung."""
        with patch.object(arbiter.decision_engine, 'decide', return_value=(ArbiterActionType.EXPLORE, "test", [])):
            with patch.object(loop_runner, 'run_full_loop', return_value=[]):
                result = arbiter.run_cycle(loop_runner)
                
                assert isinstance(result.landscape_summary, dict)
                assert "trail_count" in result.landscape_summary
                assert "crystal_count" in result.landscape_summary
                assert "warning_count" in result.landscape_summary


class TestMainLoop:
    """Tests für die Haupt-Schleife in main.py."""

    @pytest.fixture
    def mock_workspace_manager(self):
        """Mock für WorkspaceManager."""
        with patch('main.WorkspaceManager') as mock:
            mock_instance = MagicMock()
            mock_instance.workspace_root = Path("/tmp/test_workspace")
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_pheromone_field(self):
        """Mock für PheromoneField."""
        with patch('main.PheromoneField') as mock:
            mock_instance = MagicMock()
            mock_instance.evaporate.return_value = MagicMock(
                trails_evaporated=0,
                trails_remaining=0
            )
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_loop_runner(self):
        """Mock für LoopRunner."""
        with patch('main.LoopRunner') as mock:
            mock_instance = MagicMock()
            mock_instance.run_full_loop.return_value = []
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_arbiter(self):
        """Mock für Arbiter."""
        with patch('main.Arbiter') as mock:
            mock_instance = MagicMock()
            mock_instance.run_cycle.return_value = ArbiterCycleResult(
                action=ArbiterActionType.EXPLORE,
                reasoning="test reasoning",
                loop_name=LoopName.LOOP_B_EXPERIMENT,
                loop_results=[],
                landscape_summary={"trail_count": 0}
            )
            mock.return_value = mock_instance
            yield mock_instance

    def test_run_myrmex_initializes_workspace(self, mock_workspace_manager, mock_pheromone_field, mock_loop_runner, mock_arbiter):
        """run_myrmex initialisiert den Workspace."""
        from main import run_myrmex
        
        run_myrmex(max_cycles=1)
        
        # Prüfen, dass initialize aufgerufen wurde
        assert mock_workspace_manager.initialize.called

    def test_run_myrmex_runs_cycles(self, mock_workspace_manager, mock_pheromone_field, mock_loop_runner, mock_arbiter):
        """run_myrmex führt Zyklen aus."""
        from main import run_myrmex
        
        run_myrmex(max_cycles=3)
        
        # Prüfen, dass run_cycle 3 mal aufgerufen wurde
        assert mock_arbiter.run_cycle.call_count == 3

    def test_run_myrmex_respects_max_cycles(self, mock_workspace_manager, mock_pheromone_field, mock_loop_runner, mock_arbiter):
        """run_myrmex respektiert max_cycles."""
        from main import run_myrmex
        
        run_myrmex(max_cycles=5)
        
        # Prüfen, dass run_cycle genau 5 mal aufgerufen wurde
        assert mock_arbiter.run_cycle.call_count == 5
        
        # evaporate sollte auch 5 mal aufgerufen werden
        assert mock_pheromone_field.evaporate.call_count == 5

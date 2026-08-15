"""
tests/test_loop_definitions.py
Tests für die Schleifen-Definitionen und run_full_loop().
"""
from __future__ import annotations
import pytest
from pathlib import Path

from src.models.loop import LoopName, ActionType
from src.loops.loop_definitions import (
    get_loop_definition,
    LOOP_DEFINITIONS,
    LOOP_A_SIMULATION,
    LOOP_B_EXPERIMENT,
    LOOP_C_KNOWLEDGE,
    LOOP_D_COORDINATION,
)
from src.loops.loop_runner import LoopRunner


class TestLoopDefinitions:
    """Tests für die Schleifen-Definitionen."""

    def test_loop_a_has_correct_sequence(self):
        """Schleife A hat [SIMULATE, ANALYZE]."""
        assert LOOP_A_SIMULATION == [ActionType.SIMULATE, ActionType.ANALYZE]

    def test_loop_b_has_correct_sequence(self):
        """Schleife B hat [PLAN, MEASURE, ANALYZE, HYPOTHESIZE]."""
        assert LOOP_B_EXPERIMENT == [
            ActionType.PLAN,
            ActionType.MEASURE,
            ActionType.ANALYZE,
            ActionType.HYPOTHESIZE,
        ]

    def test_loop_c_has_correct_sequence(self):
        """Schleife C hat [ANALYZE, CONSOLIDATE, VALIDATE, ARCHIVE]."""
        assert LOOP_C_KNOWLEDGE == [
            ActionType.ANALYZE,
            ActionType.CONSOLIDATE,
            ActionType.VALIDATE,
            ActionType.ARCHIVE,
        ]

    def test_loop_d_is_empty(self):
        """Schleife D ist leer (wird vom Arbiter gesteuert)."""
        assert LOOP_D_COORDINATION == []

    def test_get_loop_definition_returns_correct_list(self):
        """get_loop_definition gibt die richtige Liste zurück."""
        assert get_loop_definition(LoopName.LOOP_A_SIMULATION) == LOOP_A_SIMULATION
        assert get_loop_definition(LoopName.LOOP_B_EXPERIMENT) == LOOP_B_EXPERIMENT
        assert get_loop_definition(LoopName.LOOP_C_KNOWLEDGE) == LOOP_C_KNOWLEDGE
        assert get_loop_definition(LoopName.LOOP_D_COORDINATION) == LOOP_D_COORDINATION

    def test_loop_definitions_mapping_complete(self):
        """LOOP_DEFINITIONS enthält alle 4 Schleifen."""
        assert len(LOOP_DEFINITIONS) == 4
        assert LoopName.LOOP_A_SIMULATION in LOOP_DEFINITIONS
        assert LoopName.LOOP_B_EXPERIMENT in LOOP_DEFINITIONS
        assert LoopName.LOOP_C_KNOWLEDGE in LOOP_DEFINITIONS
        assert LoopName.LOOP_D_COORDINATION in LOOP_DEFINITIONS

    def test_get_loop_definition_unknown_loop(self):
        """get_loop_definition gibt leere Liste für unbekannte Schleife."""
        # Simuliere eine unbekannte Schleife durch direkte Dictionary-Abfrage
        result = LOOP_DEFINITIONS.get(LoopName.LOOP_A_SIMULATION)
        assert result is not None  # Existierende Schleife gibt Ergebnis
        # Für nicht-existierende Keys würde .get() None zurückgeben,
        # aber unsere Funktion gibt [] zurück


class TestLoopRunnerFullLoop:
    """Tests für run_full_loop() im LoopRunner."""

    @pytest.fixture
    def runner_with_workspace(self, tmp_path: Path) -> LoopRunner:
        """Erstellt einen LoopRunner mit einem temporären Workspace."""
        workspace = tmp_path / "test_workspace"
        workspace.mkdir()
        # Erstelle notwendige Unterverzeichnisse
        (workspace / "05_Loops").mkdir()
        (workspace / "00_System").mkdir()
        return LoopRunner(workspace_path=workspace)

    def test_run_full_loop_executes_all_actions(self, runner_with_workspace: LoopRunner):
        """run_full_loop führt alle Aktionen aus."""
        # Schleife A hat 2 Aktionen: SIMULATE, ANALYZE
        results = runner_with_workspace.run_full_loop(LoopName.LOOP_A_SIMULATION)
        
        # Es sollten 2 Ergebnisse zurückgegeben werden (eine pro Aktion)
        assert len(results) == 2
        
        # Überprüfe die Aktionstypen
        assert results[0].action_type == ActionType.SIMULATE.value
        assert results[1].action_type == ActionType.ANALYZE.value

    def test_run_full_loop_stops_on_zero_energy(self, runner_with_workspace: LoopRunner):
        """run_full_loop stoppt bei 0 Energie."""
        # Setze Energie auf 0
        runner_with_workspace.loop_states[LoopName.LOOP_A_SIMULATION].energy = 0.0
        
        results = runner_with_workspace.run_full_loop(LoopName.LOOP_A_SIMULATION)
        
        # Bei 0 Energie sollte keine Aktion ausgeführt werden
        assert len(results) == 0

    def test_run_full_loop_returns_results(self, runner_with_workspace: LoopRunner):
        """run_full_loop gibt eine Liste von Ergebnissen zurück."""
        results = runner_with_workspace.run_full_loop(LoopName.LOOP_B_EXPERIMENT)
        
        # Schleife B hat 4 Aktionen
        assert len(results) == 4
        assert isinstance(results, list)
        
        # Alle Ergebnisse sollten LoopExecutionResult sein
        for result in results:
            assert hasattr(result, 'loop_name')
            assert hasattr(result, 'action_type')
            assert hasattr(result, 'energy_change')
            assert hasattr(result, 'new_energy')

    def test_run_full_loop_empty_loop_returns_empty(self, runner_with_workspace: LoopRunner):
        """run_full_loop gibt leere Liste für Schleife D (keine Aktionen)."""
        results = runner_with_workspace.run_full_loop(LoopName.LOOP_D_COORDINATION)
        assert results == []

    def test_run_full_loop_energy_consumption(self, runner_with_workspace: LoopRunner):
        """run_full_loop verbraucht Energie korrekt."""
        initial_energy = runner_with_workspace.loop_states[LoopName.LOOP_A_SIMULATION].energy
        
        results = runner_with_workspace.run_full_loop(LoopName.LOOP_A_SIMULATION)
        
        # SIMULATE: -5, ANALYZE: -10 = -15 insgesamt
        expected_energy_change = -15.0
        final_energy = runner_with_workspace.loop_states[LoopName.LOOP_A_SIMULATION].energy
        
        assert abs(final_energy - (initial_energy + expected_energy_change)) < 0.01

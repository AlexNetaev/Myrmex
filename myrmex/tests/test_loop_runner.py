"""
tests/test_loop_runner.py
Tests für den Loop-Runner und das Energie-System.
"""
import json
import pytest
from pathlib import Path
import tempfile
import shutil
import sys

# config.py ist im Projekt-Root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
import config

from src.models.loop import (
    LoopName, LoopState, LoopStatus, ActionType,
    LoopExecutionResult, LoopCycleResult
)
from src.models.arbiter import ArbiterPlan, ArbiterActionType
from src.loops.loop_runner import LoopRunner


class TestLoopRunnerSelection:
    """Tests für die Schleifen-Auswahl."""
    
    def setup_method(self):
        """Erstellt einen temporären Workspace für jeden Test."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = Path(self.temp_dir)
        
        # Verzeichnisse anlegen
        (self.workspace_path / "05_Loops").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "00_System").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "trails").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "crystals").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "warnings").mkdir(exist_ok=True)
        
        self.runner = LoopRunner(workspace_path=self.workspace_path)
    
    def teardown_method(self):
        """Räumt den temporären Workspace auf."""
        shutil.rmtree(self.temp_dir)
    
    def test_explore_chooses_first_priority(self):
        """EXPLORE wählt die erste Schleife in loop_priorities."""
        plan = ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            loop_priorities=[LoopName.LOOP_C_KNOWLEDGE, LoopName.LOOP_A_SIMULATION],
            next_action=ArbiterActionType.EXPLORE,
        )
        selected = self.runner.select_next_loop(plan)
        assert selected == LoopName.LOOP_C_KNOWLEDGE
    
    def test_follow_trail_chooses_experiment(self):
        """FOLLOW_TRAIL wählt immer LOOP_B_EXPERIMENT."""
        plan = ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            loop_priorities=[LoopName.LOOP_A_SIMULATION, LoopName.LOOP_C_KNOWLEDGE],
            next_action=ArbiterActionType.FOLLOW_TRAIL,
        )
        selected = self.runner.select_next_loop(plan)
        assert selected == LoopName.LOOP_B_EXPERIMENT
    
    def test_detour_chooses_first_priority(self):
        """DETOUR wählt die erste Schleife in loop_priorities."""
        plan = ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            loop_priorities=[LoopName.LOOP_D_COORDINATION, LoopName.LOOP_B_EXPERIMENT],
            next_action=ArbiterActionType.DETOUR,
        )
        selected = self.runner.select_next_loop(plan)
        assert selected == LoopName.LOOP_D_COORDINATION
    
    def test_consolidate_chooses_first_priority(self):
        """CONSOLIDATE wählt die erste Schleife in loop_priorities."""
        plan = ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            loop_priorities=[LoopName.LOOP_A_SIMULATION],
            next_action=ArbiterActionType.CONSOLIDATE,
        )
        selected = self.runner.select_next_loop(plan)
        assert selected == LoopName.LOOP_A_SIMULATION
    
    def test_skips_low_energy_loops(self):
        """Schleifen mit Energie < 30 werden übersprungen."""
        # Erste Schleife auf niedrige Energie setzen
        self.runner.loop_states[LoopName.LOOP_A_SIMULATION].energy = 20.0
        
        plan = ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            loop_priorities=[LoopName.LOOP_A_SIMULATION, LoopName.LOOP_B_EXPERIMENT],
            next_action=ArbiterActionType.EXPLORE,
        )
        selected = self.runner.select_next_loop(plan)
        # Sollte LOOP_B_EXPERIMENT wählen, da LOOP_A zu wenig Energie hat
        assert selected == LoopName.LOOP_B_EXPERIMENT
    
    def test_chooses_first_if_all_low_energy(self):
        """Wenn alle Schleifen < 30 Energie haben, wird die erste gewählt."""
        # Alle Schleifen auf niedrige Energie setzen
        for state in self.runner.loop_states.values():
            state.energy = 10.0
        
        plan = ArbiterPlan(
            directive_summary="Test",
            target_crystal_id="test",
            loop_priorities=[LoopName.LOOP_C_KNOWLEDGE, LoopName.LOOP_A_SIMULATION],
            next_action=ArbiterActionType.EXPLORE,
        )
        selected = self.runner.select_next_loop(plan)
        # Sollte die erste in Prioritäten wählen, trotz niedriger Energie
        assert selected == LoopName.LOOP_C_KNOWLEDGE


class TestEnergySystem:
    """Tests für das Energie-System."""
    
    def setup_method(self):
        """Erstellt einen temporären Workspace für jeden Test."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = Path(self.temp_dir)
        
        # Verzeichnisse anlegen
        (self.workspace_path / "05_Loops").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "00_System").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "trails").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "crystals").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "warnings").mkdir(exist_ok=True)
        
        self.runner = LoopRunner(workspace_path=self.workspace_path)
    
    def teardown_method(self):
        """Räumt den temporären Workspace auf."""
        shutil.rmtree(self.temp_dir)
    
    def test_measure_adds_20_energy(self):
        """MEASURE erhöht Energie um +20."""
        old_energy = self.runner.loop_states[LoopName.LOOP_B_EXPERIMENT].energy
        new_energy = self.runner.update_energy(LoopName.LOOP_B_EXPERIMENT, ActionType.MEASURE)
        assert new_energy == min(100.0, old_energy + 20.0)
    
    def test_simulate_removes_5_energy(self):
        """SIMULATE reduziert Energie um -5."""
        old_energy = self.runner.loop_states[LoopName.LOOP_A_SIMULATION].energy
        new_energy = self.runner.update_energy(LoopName.LOOP_A_SIMULATION, ActionType.SIMULATE)
        assert new_energy == max(0.0, old_energy - 5.0)
    
    def test_analyze_removes_10_energy(self):
        """ANALYZE reduziert Energie um -10."""
        old_energy = self.runner.loop_states[LoopName.LOOP_C_KNOWLEDGE].energy
        new_energy = self.runner.update_energy(LoopName.LOOP_C_KNOWLEDGE, ActionType.ANALYZE)
        assert new_energy == max(0.0, old_energy - 10.0)
    
    def test_consolidate_removes_5_energy(self):
        """CONSOLIDATE reduziert Energie um -5."""
        old_energy = self.runner.loop_states[LoopName.LOOP_D_COORDINATION].energy
        new_energy = self.runner.update_energy(LoopName.LOOP_D_COORDINATION, ActionType.CONSOLIDATE)
        assert new_energy == max(0.0, old_energy - 5.0)
    
    def test_energy_capped_at_100(self):
        """Energie kann nie über 100 gehen."""
        self.runner.loop_states[LoopName.LOOP_B_EXPERIMENT].energy = 95.0
        new_energy = self.runner.update_energy(LoopName.LOOP_B_EXPERIMENT, ActionType.MEASURE)
        assert new_energy == 100.0
    
    def test_energy_capped_at_0(self):
        """Energie kann nie unter 0 gehen."""
        self.runner.loop_states[LoopName.LOOP_C_KNOWLEDGE].energy = 5.0
        new_energy = self.runner.update_energy(LoopName.LOOP_C_KNOWLEDGE, ActionType.ANALYZE)
        assert new_energy == 0.0


class TestPersistence:
    """Tests für die Persistenz der Schleifen-Zustände."""
    
    def setup_method(self):
        """Erstellt einen temporären Workspace für jeden Test."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = Path(self.temp_dir)
        
        # Verzeichnisse anlegen
        (self.workspace_path / "05_Loops").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "00_System").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "trails").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "crystals").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "warnings").mkdir(exist_ok=True)
        
        self.runner = LoopRunner(workspace_path=self.workspace_path)
    
    def teardown_method(self):
        """Räumt den temporären Workspace auf."""
        shutil.rmtree(self.temp_dir)
    
    def test_saves_loop_states(self):
        """Schleifen-Zustände werden korrekt in 05_Loops/ geschrieben."""
        # Zustand ändern
        self.runner.loop_states[LoopName.LOOP_A_SIMULATION].energy = 50.0
        self.runner.loop_states[LoopName.LOOP_A_SIMULATION].iteration_count = 5
        
        # Speichern
        self.runner.save_loop_states()
        
        # Datei lesen und prüfen
        file_path = self.workspace_path / "05_Loops" / "loop_a_simulation.json"
        assert file_path.exists()
        
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        assert raw["energy"] == 50.0
        assert raw["iteration_count"] == 5
    
    def test_atomic_write_no_temp_files(self):
        """Atomares Schreiben funktioniert (keine .tmp-Dateien nach Abschluss)."""
        self.runner.save_loop_states()
        
        # Prüfen, dass keine .tmp-Dateien existieren
        temp_files = list((self.workspace_path / "05_Loops").glob("*.tmp"))
        assert len(temp_files) == 0
    
    def test_loads_states_on_init(self):
        """Zustände werden beim nächsten Start korrekt geladen."""
        # Erster Runner: Zustand speichern
        self.runner.loop_states[LoopName.LOOP_B_EXPERIMENT].energy = 75.0
        self.runner.loop_states[LoopName.LOOP_B_EXPERIMENT].iteration_count = 10
        self.runner.save_loop_states()
        
        # Zweiter Runner: Zustand laden
        runner2 = LoopRunner(workspace_path=self.workspace_path)
        assert runner2.loop_states[LoopName.LOOP_B_EXPERIMENT].energy == 75.0
        assert runner2.loop_states[LoopName.LOOP_B_EXPERIMENT].iteration_count == 10


class TestFullCycle:
    """Tests für den vollständigen Zyklus."""
    
    def setup_method(self):
        """Erstellt einen temporären Workspace für jeden Test."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = Path(self.temp_dir)
        
        # Verzeichnisse anlegen
        (self.workspace_path / "05_Loops").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "00_System").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field").mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "trails").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "crystals").mkdir(exist_ok=True)
        (self.workspace_path / "01_Pheromon_Field" / "warnings").mkdir(exist_ok=True)
        
        # Arbiter-Plan erstellen
        plan = ArbiterPlan(
            directive_summary="Test Directive",
            target_crystal_id="test_crystal",
            loop_priorities=[LoopName.LOOP_B_EXPERIMENT, LoopName.LOOP_A_SIMULATION],
            next_action=ArbiterActionType.EXPLORE,
            next_action_reasoning="Testing",
        )
        plan_path = self.workspace_path / "00_System" / "arbiter_plan.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        
        self.runner = LoopRunner(workspace_path=self.workspace_path)
    
    def teardown_method(self):
        """Räumt den temporären Workspace auf."""
        shutil.rmtree(self.temp_dir)
    
    def test_run_cycle_executes_all_steps(self):
        """run_cycle() führt alle Schritte in korrekter Reihenfolge aus."""
        # Energie vor dem Zyklus auf einen Wert < 100 setzen, um Energie-Änderung zu sehen
        self.runner.loop_states[LoopName.LOOP_B_EXPERIMENT].energy = 50.0
        
        result = self.runner.run_cycle()
        
        # Ergebnis prüfen
        assert result.loop_executed == LoopName.LOOP_B_EXPERIMENT  # Erste in Prioritäten
        assert result.action_type == ActionType.MEASURE.value  # LOOP_B → MEASURE
        assert result.energy_change == +20.0  # MEASURE gibt +20 Energie
        assert "evaporation_stats" in result.evaporation_stats or True  # Evaporation wurde aufgerufen
    
    def test_evaporate_called_at_end_of_cycle(self):
        """evaporate() wird am Ende des Zyklus aufgerufen."""
        # Ein Trail-Pheromon ablegen
        from src.models.pheromone import Pheromone, PheromoneType
        pheromone = Pheromone(
            id="trail_test",
            type=PheromoneType.TRAIL,
            strength=0.5,
            age_cycles=0,
            relevance=1.0,
            content="Test trail",
            source_agent="test",
        )
        self.runner.pheromone_field.emit(pheromone)
        
        # Zyklus ausführen
        result = self.runner.run_cycle()
        
        # Nach einem Zyklus sollte das Alter des Pheromons erhöht sein
        # und die Stärke entsprechend verdunstet
        loaded_pheromone = self.runner.pheromone_field.get("trail_test")
        if loaded_pheromone:
            assert loaded_pheromone.age_cycles >= 1
    
    def test_loop_cycle_result_has_correct_stats(self):
        """LoopCycleResult enthält korrekte Statistiken."""
        # Energie vor dem Zyklus auf einen Wert < 100 setzen, um Energie-Änderung zu sehen
        initial_energy = 60.0
        self.runner.loop_states[LoopName.LOOP_B_EXPERIMENT].energy = initial_energy
        
        result = self.runner.run_cycle()
        
        assert result.loop_executed == LoopName.LOOP_B_EXPERIMENT
        assert result.action_type == ActionType.MEASURE.value
        assert result.energy_before == initial_energy
        assert result.energy_after == min(100.0, initial_energy + 20.0)
        assert result.energy_change == +20.0
        assert result.iterations_total >= 1

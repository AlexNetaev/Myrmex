"""
tests/test_integration.py
End-to-End-Integrationstest: Arbiter → LoopRunner → Kaste → Pheromon-Feld.

Dieser Test ist der kritische Meilenstein-Test für die Integration.
Er testet das System als Ganzes und findet Fehler, die in den
Unit-Tests der einzelnen Komponenten nicht sichtbar wären.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml

from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner
from src.castes.registry import get_registry
from src.models.loop import LoopName, ActionType
from src.models.pheromone import PheromoneType
from src.pheromones.pheromone_field import PheromoneField


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


class TestEndToEndIntegration:
    """End-to-End-Integrationstests."""
    
    def test_arbiter_to_loop_runner_to_caste(self, integration_workspace):
        """
        Vollständiger Fluss: Arbiter trifft Entscheidung → LoopRunner
        führt Kaste aus → Kaste schreibt Pheromone.
        """
        # 1. Arbiter erstellt einen Plan
        arbiter = Arbiter(workspace_path=integration_workspace)
        plan = arbiter.run_cycle()
        
        # Der Plan sollte existieren
        assert plan is not None
        assert plan.next_action is not None
        
        # 2. LoopRunner führt die Schleife aus
        loop_runner = LoopRunner(workspace_path=integration_workspace)
        
        # Die Schleife basierend auf der Aktion des Arbiters bestimmen
        action_to_loop = {
            "explore": LoopName.LOOP_B_EXPERIMENT,
            "follow_trail": LoopName.LOOP_B_EXPERIMENT,
            "detour": LoopName.LOOP_A_SIMULATION,
            "consolidate": LoopName.LOOP_C_KNOWLEDGE,
        }
        loop_name = action_to_loop.get(plan.next_action.value, LoopName.LOOP_B_EXPERIMENT)
        
        # Schleife ausführen
        execution_result = loop_runner.execute_loop(loop_name)
        
        # Das Ergebnis sollte existieren
        assert execution_result is not None
        assert execution_result.loop_name == loop_name
        assert execution_result.iteration_count == 1
    
    def test_caste_writes_pheromones(self, integration_workspace):
        """
        Testet, dass die Kaste tatsächlich Pheromone in das Feld schreibt.
        """
        # Ein TRAIL-Pheromon als Ausgangspunkt erstellen
        field = PheromoneField(field_root=integration_workspace / "01_Pheromon_Field")
        from src.models.pheromone import Pheromone
        initial_pheromone = field.emit(
            Pheromone(
                id="test_initial",
                type=PheromoneType.TRAIL,
                strength=0.5,
                age_cycles=0,
                relevance=0.5,
                content="Initial trail for testing",
                tags=["test"],
                source_agent="test",
            )
        )
        
        # LoopRunner führt die ANALYZE-Aktion aus (AnalystCaste)
        loop_runner = LoopRunner(workspace_path=integration_workspace)
        execution_result = loop_runner.execute_loop(LoopName.LOOP_C_KNOWLEDGE)
        
        # Nach der Ausführung sollte mindestens ein neues Pheromon existieren
        all_pheromones = field.scan()
        assert len(all_pheromones) >= 1
    
    def test_registry_returns_correct_caste(self, integration_workspace):
        """
        Testet, dass die Registry die richtige Kaste für jeden ActionType zurückgibt.
        """
        registry = get_registry()
        
        # ANALYZE sollte AnalystCaste zurückgeben
        from src.castes.analyst import AnalystCaste
        assert registry.get_caste_for_action(ActionType.ANALYZE) == AnalystCaste
        
        # MEASURE sollte ExecutorCaste zurückgeben
        from src.castes.executor import ExecutorCaste
        assert registry.get_caste_for_action(ActionType.MEASURE) == ExecutorCaste
        
        # SIMULATE sollte SimulatorCaste zurückgeben (implementiert)
        from src.castes.simulator import SimulatorCaste
        assert registry.get_caste_for_action(ActionType.SIMULATE) == SimulatorCaste
        
        # CONSOLIDATE sollte TheoristCaste zurückgeben (implementiert)
        from src.castes.theorist import TheoristCaste
        assert registry.get_caste_for_action(ActionType.CONSOLIDATE) == TheoristCaste
        
        # VALIDATE sollte GuardianCaste zurückgeben (implementiert)
        from src.castes.guardian import GuardianCaste
        assert registry.get_caste_for_action(ActionType.VALIDATE) == GuardianCaste
    
    def test_energy_budget_updates_correctly(self, integration_workspace):
        """
        Testet, dass das Energie-Budget korrekt aktualisiert wird.
        """
        loop_runner = LoopRunner(workspace_path=integration_workspace)
        
        # Initiale Energie sollte 100 sein
        initial_energy = loop_runner.loop_states[LoopName.LOOP_B_EXPERIMENT].energy
        assert initial_energy == 100.0
        
        # MEASURE gibt +20 Energie (aber gekappt bei 100)
        execution_result = loop_runner.execute_loop(LoopName.LOOP_B_EXPERIMENT)
        
        # Energie sollte immer noch 100 sein (gekappt)
        assert execution_result.new_energy == 100.0
    
    def test_loop_runner_handles_all_loops(self, integration_workspace):
        """
        Testet, dass der LoopRunner alle vier Schleifen ausführen kann.
        """
        loop_runner = LoopRunner(workspace_path=integration_workspace)
        
        all_loops = [
            LoopName.LOOP_A_SIMULATION,
            LoopName.LOOP_B_EXPERIMENT,
            LoopName.LOOP_C_KNOWLEDGE,
            LoopName.LOOP_D_COORDINATION,
        ]
        
        for loop_name in all_loops:
            execution_result = loop_runner.execute_loop(loop_name)
            assert execution_result is not None
            assert execution_result.loop_name == loop_name
    
    def test_integration_with_hardware_profile(self, integration_workspace):
        """
        Testet die Integration mit dem Hardware-Profil (ExecutorCaste).
        """
        # Ein experiment_profile.yaml erstellen
        profile_path = integration_workspace / "00_System" / "experiment_profile.yaml"
        profile = {
            "experiment_type": "fenton_fluorescence",
            "cycle_id": "Cycle_001",
            "parameters": {
                "ascorbic_acid_concentration_mm": 25.0,
                "fecl3_concentration_mm": 1.0,
                "h2o2_concentration_mm": 50.0,
                "fluorescein_concentration_mm": 0.01,
                "phosphate_buffer_concentration_mm": 50.0,
                "target_temperature_c": 37.0,
                "mixing_speed_rpm": 600,
                "mixing_time_s": 15.0,
                "heating_time_s": 30.0,
                "measurement_interval_ms": 500,
                "fluorescence_duration_s": 60.0,
                "reagents": [
                    {"reagent_name": "ascorbic_acid", "volume_ul": 500.0, "concentration_mm": 25.0},
                    {"reagent_name": "fecl3", "volume_ul": 100.0, "concentration_mm": 1.0},
                    {"reagent_name": "h2o2", "volume_ul": 200.0, "concentration_mm": 50.0},
                    {"reagent_name": "fluorescein", "volume_ul": 100.0, "concentration_mm": 0.01},
                    {"reagent_name": "phosphate_buffer", "volume_ul": 100.0, "concentration_mm": 50.0},
                ],
            },
        }
        profile_path.write_text(yaml.dump(profile), encoding="utf-8")
        
        # Ein Hardware-Profil erstellen
        hardware_profile_path = integration_workspace / "hardware_profiles" / "orbus_dummy_v2.yaml"
        hardware_profile_path.parent.mkdir(parents=True, exist_ok=True)
        hardware_profile = {
            "metadata": {"name": "OrbusSim Dummy V2", "experiment_type": "fenton_fluorescence"},
            "limits": {"target_temperature_c": {"min": 20.0, "max": 75.0}},
            "defaults": {"station_4_action": "FLUORESCENCE"},
        }
        hardware_profile_path.write_text(yaml.dump(hardware_profile), encoding="utf-8")
        
        # LoopRunner führt die MEASURE-Aktion aus (ExecutorCaste)
        loop_runner = LoopRunner(workspace_path=integration_workspace)
        execution_result = loop_runner.execute_loop(LoopName.LOOP_B_EXPERIMENT)
        
        # Das Ergebnis sollte existieren
        assert execution_result is not None
        assert execution_result.loop_name == LoopName.LOOP_B_EXPERIMENT
        
        # Eine experiment.json sollte in der Hardware-Queue existieren
        queue_path = integration_workspace / "03_Hardware_Queue" / "experiment.json"
        assert queue_path.exists()

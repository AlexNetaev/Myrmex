"""
tests/test_decision.py
Tests für den DecisionEngine.
"""
import pytest

from src.models.landscape import LandscapeSummary
from src.models.arbiter import ArbiterActionType
from src.models.directive import TargetCrystal
from src.models.loop import LoopName
from src.arbiter.decision import DecisionEngine


@pytest.fixture
def decision_engine():
    """Erstellt eine DecisionEngine für Tests."""
    return DecisionEngine()


class TestDecisionEngineTargetAchieved:
    """Tests wenn Ziel-Kristall erreicht ist."""
    
    def test_target_achieved_consolidates(self, decision_engine):
        """Ziel-Kristall erreicht → CONSOLIDATE."""
        landscape = LandscapeSummary()
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={"value": 1.0},
            achieved=True,
        )
        
        action, reasoning, priorities = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        assert action == ArbiterActionType.CONSOLIDATE
        assert "achieved" in reasoning.lower()
        assert priorities == decision_engine._default_loop_priorities()


class TestDecisionEngineWarning:
    """Tests bei Warnungen."""
    
    def test_warning_detected_detours(self, decision_engine):
        """Warnung vorhanden → DETOUR."""
        landscape = LandscapeSummary(
            has_warning_nearby=True,
            strongest_warning_id="warning_1",
        )
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={"value": 1.0},
            achieved=False,
        )
        
        action, reasoning, priorities = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        assert action == ArbiterActionType.DETOUR
        assert "warning" in reasoning.lower()
        assert priorities == decision_engine._detour_loop_priorities()


class TestDecisionEngineSparse:
    """Tests bei dünner Landschaft."""
    
    def test_sparse_landscape_explores(self, decision_engine):
        """Landschaft dünn → EXPLORE."""
        landscape = LandscapeSummary(
            is_sparse=True,
            has_warning_nearby=False,
            trail_count=1,
            crystal_count=0,
        )
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={"value": 1.0},
            achieved=False,
        )
        
        action, reasoning, priorities = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        assert action == ArbiterActionType.EXPLORE
        assert "sparse" in reasoning.lower()
        assert priorities == decision_engine._explore_loop_priorities()


class TestDecisionEngineStrongTrail:
    """Tests bei starkem Trail."""
    
    def test_strong_trail_follows(self, decision_engine):
        """Starker Trail vorhanden → FOLLOW_TRAIL."""
        landscape = LandscapeSummary(
            is_sparse=False,
            has_warning_nearby=False,
            has_strong_trail=True,
            strongest_trail_id="trail_1",
        )
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={"value": 1.0},
            achieved=False,
        )
        
        action, reasoning, priorities = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        assert action == ArbiterActionType.FOLLOW_TRAIL
        assert "trail" in reasoning.lower()
        assert priorities == decision_engine._follow_trail_loop_priorities()


class TestDecisionEngineDefault:
    """Tests für Default-Entscheidungen."""
    
    def test_no_clear_direction_consolidates(self, decision_engine):
        """Keine klare Richtung → CONSOLIDATE (Default)."""
        landscape = LandscapeSummary(
            is_sparse=False,
            has_warning_nearby=False,
            has_strong_trail=False,
        )
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={"value": 1.0},
            achieved=False,
        )
        
        action, reasoning, priorities = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        assert action == ArbiterActionType.CONSOLIDATE
        assert "moderate" in reasoning.lower() or "consolidat" in reasoning.lower()
        assert priorities == decision_engine._default_loop_priorities()


class TestLoopPriorities:
    """Tests für Loop-Prioritäten."""
    
    def test_default_loop_priorities(self, decision_engine):
        """Standard-Prioritäten korrekt."""
        priorities = decision_engine._default_loop_priorities()
        
        assert len(priorities) == 4
        assert priorities[0] == LoopName.LOOP_B_EXPERIMENT
        assert priorities[1] == LoopName.LOOP_A_SIMULATION
        assert priorities[2] == LoopName.LOOP_C_KNOWLEDGE
        assert priorities[3] == LoopName.LOOP_D_COORDINATION
    
    def test_explore_loop_priorities(self, decision_engine):
        """EXPLORE-Prioritäten korrekt."""
        priorities = decision_engine._explore_loop_priorities()
        
        assert len(priorities) == 4
        assert priorities[0] == LoopName.LOOP_B_EXPERIMENT
        assert priorities[1] == LoopName.LOOP_A_SIMULATION
    
    def test_follow_trail_loop_priorities(self, decision_engine):
        """FOLLOW_TRAIL-Prioritäten korrekt."""
        priorities = decision_engine._follow_trail_loop_priorities()
        
        assert len(priorities) == 4
        assert priorities[0] == LoopName.LOOP_B_EXPERIMENT
    
    def test_detour_loop_priorities(self, decision_engine):
        """DETOUR-Prioritäten korrekt."""
        priorities = decision_engine._detour_loop_priorities()
        
        assert len(priorities) == 4
        # Bei DETOUR wird zuerst simuliert (sicher)
        assert priorities[0] == LoopName.LOOP_A_SIMULATION
        assert priorities[2] == LoopName.LOOP_B_EXPERIMENT  # Experiment kommt später


class TestDecisionPriority:
    """Tests für die Priorität der Entscheidungen."""
    
    def test_warning_over_sparse(self, decision_engine):
        """Warnung hat Vorrang vor spärlicher Landschaft."""
        landscape = LandscapeSummary(
            is_sparse=True,
            has_warning_nearby=True,
        )
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={},
            achieved=False,
        )
        
        action, _, _ = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        # Warnung sollte Vorrang haben
        assert action == ArbiterActionType.DETOUR
    
    def test_target_achieved_over_all(self, decision_engine):
        """Ziel erreicht hat Vorrang vor allem."""
        landscape = LandscapeSummary(
            is_sparse=True,
            has_warning_nearby=True,
            has_strong_trail=True,
        )
        target_crystal = TargetCrystal(
            id="target_1",
            description="Test target",
            criteria={},
            achieved=True,
        )
        
        action, _, _ = decision_engine.decide(
            landscape=landscape,
            target_crystal=target_crystal,
            current_plan=None,
        )
        
        # Ziel erreicht sollte Vorrang haben
        assert action == ArbiterActionType.CONSOLIDATE

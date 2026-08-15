"""
src/castes/registry.py
Die Kasten-Registry — zentrales Mapping zwischen Aktionstyp und Kaste.

Diese Registry ist der "Vermittler" zwischen dem LoopRunner und den
tatsächlichen Kasten. Der LoopRunner fragt die Registry: "Welche Kaste
soll ich für diese Aktion ausführen?" und die Registry gibt die
richtige Kasten-Klasse zurück.

Die Registry ist bewusst erweiterbar gestaltet: Neue Kasten können
einfach registriert werden, ohne den LoopRunner oder den Arbiter zu
ändern. Noch fehlende Kasten werden vorerst mit der PlaceholderCaste
abgedeckt.
"""
from __future__ import annotations
import logging
from typing import Type

from src.models.loop import ActionType
from src.models.caste import CasteName
from src.castes.base_caste import BaseCaste
from src.castes.placeholder import PlaceholderCaste
from src.castes.analyst import AnalystCaste
from src.castes.planner import PlannerCaste
from src.castes.executor import ExecutorCaste
from src.castes.simulator import SimulatorCaste
from src.castes.theorist import TheoristCaste
from src.castes.guardian import GuardianCaste
from src.castes.hypothesizer import HypothesizerCaste
from src.castes.archivist import ArchivistCaste

logger = logging.getLogger("castes.registry")


class CasteRegistry:
    """
    Zentrale Registry, die ein Mapping zwischen ActionType und Kaste hält.
    
    Der LoopRunner nutzt diese Registry, um die richtige Kaste für eine
    Aktion zu finden. Die Registry ist erweiterbar: Neue Kasten können
    mit `register()` registriert werden.
    
    Beispiel:
        registry = CasteRegistry()
        caste_class = registry.get_caste_for_action(ActionType.ANALYZE)
        caste = caste_class(workspace_path=some_path)
        result = caste.execute(work_dir=some_dir)
    """
    
    def __init__(self) -> None:
        """Initialisiert die Registry mit den Standard-Kasten."""
        self._registry: dict[ActionType, Type[BaseCaste]] = {}
        self._register_defaults()
    
    def _register_defaults(self) -> None:
        """
        Registriert die Standard-Kasten für die verfügbaren Aktionstypen.
        
        Noch fehlende Kasten werden mit der PlaceholderCaste abgedeckt.
        Sie können später einfach mit register() ausgetauscht werden.
        """
        # Verfügbare Kasten
        self.register(ActionType.ANALYZE, AnalystCaste)
        self.register(ActionType.MEASURE, ExecutorCaste)
        
        # SimulatorCaste jetzt implementiert
        self.register(ActionType.SIMULATE, SimulatorCaste)
        
        # TheoristCaste jetzt implementiert
        self.register(ActionType.CONSOLIDATE, TheoristCaste)
        
        # GuardianCaste jetzt implementiert
        self.register(ActionType.VALIDATE, GuardianCaste)
        
        # ArchivistCaste jetzt implementiert
        self.register(ActionType.ARCHIVE, ArchivistCaste)
        
        logger.info(
            "CasteRegistry initialized with %d action types (%d placeholders)",
            len(self._registry),
            sum(1 for c in self._registry.values() if c is PlaceholderCaste),
        )
    
    def register(self, action_type: ActionType, caste_class: Type[BaseCaste]) -> None:
        """
        Registriert eine Kaste für einen Aktionstyp.
        
        Args:
            action_type: Der Aktionstyp, für den die Kaste registriert wird.
            caste_class: Die Kasten-Klasse, die für diesen Aktionstyp
                         ausgeführt werden soll.
        
        Raises:
            ValueError: Wenn die Kasten-Klasse nicht von BaseCaste erbt.
        """
        if not issubclass(caste_class, BaseCaste):
            raise ValueError(
                f"Caste class {caste_class.__name__} must be a subclass of BaseCaste."
            )
        
        previous = self._registry.get(action_type)
        if previous is not None:
            logger.warning(
                "Overriding registration for %s: %s -> %s",
                action_type.value,
                previous.__name__,
                caste_class.__name__,
            )
        
        self._registry[action_type] = caste_class
        logger.debug("Registered %s for %s", caste_class.__name__, action_type.value)
    
    def get_caste_for_action(self, action_type: ActionType) -> Type[BaseCaste]:
        """
        Gibt die Kasten-Klasse für einen Aktionstyp zurück.
        
        Args:
            action_type: Der Aktionstyp, für den die Kaste gesucht wird.
        
        Returns:
            Die Kasten-Klasse, die für diesen Aktionstyp registriert ist.
            Falls keine Kaste registriert ist, wird PlaceholderCaste
            zurückgegeben (defensiver Fallback).
        """
        caste_class = self._registry.get(action_type)
        if caste_class is None:
            logger.warning(
                "No caste registered for %s — falling back to PlaceholderCaste.",
                action_type.value,
            )
            return PlaceholderCaste
        return caste_class
    
    def is_placeholder(self, action_type: ActionType) -> bool:
        """
        Prüft, ob für einen Aktionstyp nur ein Placeholder registriert ist.
        
        Das ist nützlich für den LoopRunner, um zu wissen, ob eine Aktion
        "echt" ausgeführt wird oder nur simuliert.
        """
        caste_class = self._registry.get(action_type)
        return caste_class is PlaceholderCaste
    
    def get_registered_actions(self) -> list[ActionType]:
        """Gibt alle registrierten Aktionstypen zurück."""
        return list(self._registry.keys())


# Globale Singleton-Instanz für einfachen Zugriff
_global_registry: CasteRegistry | None = None


def get_registry() -> CasteRegistry:
    """
    Gibt die globale Kasten-Registry zurück (Singleton).
    
    Diese Funktion ist der bevorzugte Weg, auf die Registry zuzugreifen,
    da sie sicherstellt, dass alle Komponenten dieselbe Registry-Instanz
    nutzen.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = CasteRegistry()
    return _global_registry


def reset_registry() -> None:
    """
    Setzt die globale Registry-Instanz zurück.
    
    Diese Funktion sollte in Tests verwendet werden, um eine frische
    Registry-Instanz zwischen den Tests zu erhalten und so Test-Isolation
    zu gewährleisten.
    """
    global _global_registry
    _global_registry = None

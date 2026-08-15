"""
Basisklasse für Physik-Modelle.
Erweiterbar für komplexere Simulationen in späteren Phasen.
"""
from abc import ABC, abstractmethod
from typing import Any
import numpy as np


class BasePhysics(ABC):
    """
    Abstrakte Basisklasse für Physik-Simulationen.
    
    In Phase 1 sind die Modelle deterministisch und einfach.
    In späteren Phasen können sie komplexer werden (stochastisch,
    LLM-basiert, etc.).
    """
    
    def __init__(self, seed: int | None = None):
        """
        Args:
            seed: Optionaler Seed für reproduzierbare Simulationen.
        """
        self.rng = np.random.default_rng(seed)
    
    @abstractmethod
    def simulate(self, params: dict) -> Any:
        """
        Führt die Simulation aus.
        
        Args:
            params: Parameter für die Simulation.
        
        Returns:
            Simulationsergebnis (typabhängig).
        """
        pass

"""
src/castes/
Die 9 Kasten von Myrmex — die Arbeiter des Schwarms.

Diese Phase (Phase 1) definiert die Basisklasse und die erste echte Kaste.
Weitere Kasten folgen in späteren Prompts.
"""
from .base_caste import BaseCaste
from .placeholder import PlaceholderCaste
from .analyst import AnalystCaste

__all__ = ["BaseCaste", "PlaceholderCaste", "AnalystCaste"]
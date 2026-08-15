"""
config.py
Single Source of Truth für Pfade und Konfiguration.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

# .env laden
load_dotenv()

# ---------------------------------------------------------------------------
# PROJEKT-ROOT
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# WORKSPACE-ROOT
# ---------------------------------------------------------------------------
WORKSPACE_ROOT: Path = Path(
    os.getenv("WORKSPACE_ROOT", PROJECT_ROOT / "myrmex_workspace")
).resolve()

# ---------------------------------------------------------------------------
# LLM-KONFIGURATION
# ---------------------------------------------------------------------------
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_MAX_RETRIES: int = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
OLLAMA_TIMEOUT_S: int = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
OLLAMA_CONTEXT_SIZE: int = int(os.getenv("OLLAMA_CONTEXT_SIZE", "4096"))

# ---------------------------------------------------------------------------
# WORKSPACE-VERZEICHNISSE
# ---------------------------------------------------------------------------
SYSTEM_DIR: Path = WORKSPACE_ROOT / "00_System"
PHEROMON_FIELD_DIR: Path = WORKSPACE_ROOT / "01_Pheromon_Field"
TRAILS_DIR: Path = PHEROMON_FIELD_DIR / "trails"
CRYSTALS_DIR: Path = PHEROMON_FIELD_DIR / "crystals"
WARNINGS_DIR: Path = PHEROMON_FIELD_DIR / "warnings"
RESEARCH_CYCLES_DIR: Path = WORKSPACE_ROOT / "02_Research_Cycles"
HARDWARE_QUEUE_DIR: Path = WORKSPACE_ROOT / "03_Hardware_Queue"
PROCESSED_QUEUE_DIR: Path = HARDWARE_QUEUE_DIR / "_processed"
FAILED_QUEUE_DIR: Path = HARDWARE_QUEUE_DIR / "_failed"
KNOWLEDGE_BASE_DIR: Path = WORKSPACE_ROOT / "04_Knowledge_Base"
KNOWLEDGE_BASE_ARCHIVE_DIR: Path = KNOWLEDGE_BASE_DIR / "Archive"
LOOPS_DIR: Path = WORKSPACE_ROOT / "05_Loops"

# ---------------------------------------------------------------------------
# WICHTIGE DATEIEN
# ---------------------------------------------------------------------------
DIRECTIVE_FILE: Path = SYSTEM_DIR / "directive.md"
TARGET_CRYSTAL_FILE: Path = SYSTEM_DIR / "target_crystal.json"
ARBITER_PLAN_FILE: Path = SYSTEM_DIR / "arbiter_plan.json"
EXPERIMENT_PROFILE_FILE: Path = SYSTEM_DIR / "experiment_profile.yaml"
ESTOP_FLAG_FILE: Path = SYSTEM_DIR / "ESTOP.flag"
PHEROMON_INDEX_FILE: Path = PHEROMON_FIELD_DIR / "pheromon_index.json"
THEORY_BASELINE_FILE: Path = KNOWLEDGE_BASE_DIR / "theory_baseline.md"

# ---------------------------------------------------------------------------
# KONSTANTEN
# ---------------------------------------------------------------------------
# Das Energie-Budget der Schleifen
MAX_LOOP_ENERGY: float = 100.0

# Die Verdunstungsraten (pro Zyklus)
TRAIL_EVAPORATION_RATE: float = 0.05
WARNING_EVAPORATION_RATE: float = 0.03

# Die minimale Stärke, bevor ein Pheromon entfernt wird
MIN_PHEROMONE_STRENGTH: float = 0.1

# Die maximale Anzahl von Zyklen, die der Arbiter vorausplant
MAX_ARBITER_LOOKAHEAD: int = 3

# ---------------------------------------------------------------------------
# PHEROMON-FELD-KONSTANTEN
# ---------------------------------------------------------------------------
REINFORCE_AMOUNT: float = 0.1        # Stärke-Erhöhung bei Nutzung
WEAKEN_AMOUNT: float = 0.2           # Stärke-Reduktion bei Widerlegung
CRYSTALLIZE_THRESHOLD: float = 0.9   # Schwellenwert für Auto-Kristallisierung
CRYSTAL_REINFORCE_AMOUNT: float = 0.0  # Kristalle werden nicht weiter verstärkt
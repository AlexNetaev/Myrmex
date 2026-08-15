"""
Konfiguration für den Hardware-Dummy.
"""
from pathlib import Path
import os

# Workspace-Root (kann über Umgebungsvariable überschrieben werden)
WORKSPACE_ROOT = Path(
    os.getenv("MYRMEX_WORKSPACE", Path(__file__).resolve().parent.parent / "myrmex_workspace")
)

# Queue-Verzeichnis
QUEUE_DIR = WORKSPACE_ROOT / "03_Hardware_Queue"

# Poll-Intervall in Sekunden
POLL_INTERVAL_S = 1.0

# Konfigurations-Dictionary
DUMMY_CONFIG = {
    "workspace_root": WORKSPACE_ROOT,
    "queue_dir": QUEUE_DIR,
    "poll_interval_s": POLL_INTERVAL_S
}

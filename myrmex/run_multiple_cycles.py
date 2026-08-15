# Erstelle eine Datei `run_multiple_cycles.py`
from src.workspace.workspace_manager import WorkspaceManager
from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner
import time

wm = WorkspaceManager()
wm.initialize()

arbiter = Arbiter(workspace_path=wm.workspace_root)
loop_runner = LoopRunner(workspace_path=wm.workspace_root)

for i in range(5):
    print(f"\n{'=' * 60}")
    print(f"Zyklus {i + 1}/5")
    print(f"{'=' * 60}")

    result = arbiter.run_cycle(loop_runner)
    print(f"Aktion: {result.action.value}")
    print(f"Schleife: {result.loop_name.value}")
    print(f"Begründung: {result.reasoning}")

    time.sleep(2)  # Kurze Pause zwischen Zyklen
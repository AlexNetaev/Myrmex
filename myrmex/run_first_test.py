"""
run_first_test.py
Erster großer Test: Ein vollständiger Zyklus durch den gesamten Schwarm.

Dieses Skript:
1. Initialisiert den Workspace
2. Führt einen vollständigen Arbiter-Zyklus aus
3. Prüft die Ergebnisse
4. Schreibt einen Bericht

Verwendung:
    python run_first_test.py
"""
import sys
import time
from pathlib import Path

# Projekt-Root bestimmen
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.workspace.workspace_manager import WorkspaceManager
from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner
from src.pheromones.pheromone_field import PheromoneField
from src.models.loop import LoopName


def main():
    """Führt den ersten großen Test aus."""
    print("=" * 70)
    print("🐜 Myrmex: Erster großer Test")
    print("=" * 70)
    
    start_time = time.time()

    # 1. Workspace initialisieren
    print("\n[1/5] Workspace initialisieren...")
    wm = WorkspaceManager()
    wm.initialize()
    print(f"  ✓ Workspace: {wm.workspace_root}")

    # 2. Arbiter und LoopRunner initialisieren
    print("\n[2/5] Arbiter und LoopRunner initialisieren...")
    arbiter = Arbiter(workspace_path=wm.workspace_root)
    loop_runner = LoopRunner(workspace_path=wm.workspace_root)
    print("  ✓ Arbiter und LoopRunner bereit")

    # 3. Zyklus ausführen
    print("\n[3/5] Zyklus ausführen...")
    try:
        cycle_result = arbiter.run_cycle(loop_runner)
        print(f"  ✓ Aktion: {cycle_result.action.value}")
        print(f"  ✓ Schleife: {cycle_result.loop_name.value}")
        print(f"  ✓ Begründung: {cycle_result.reasoning}")
    except Exception as e:
        print(f"  ✗ Fehler beim Ausführen des Zyklus: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. Ergebnisse prüfen
    print("\n[4/5] Ergebnisse prüfen...")
    field = PheromoneField(field_root=wm.workspace_root / "01_Pheromon_Field")
    all_pheromones = field.scan()
    print(f"  ✓ Pheromone im Feld: {len(all_pheromones)}")

    # Pheromone anzeigen
    for p in all_pheromones[:10]:
        tags_str = ", ".join(p.tags) if p.tags else "(keine Tags)"
        print(f"    - [{p.type.value}] ({p.source_agent}) [{tags_str}]: {p.content[:80]}...")

    # 5. Bericht schreiben
    print("\n[5/5] Bericht schreiben...")
    report_path = wm.workspace_root / "00_System" / "first_test_report.md"
    
    elapsed = time.time() - start_time
    
    report = f"""# Erster großer Test — Bericht

**Datum:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Dauer:** {elapsed:.2f} Sekunden

## Ergebnis

- **Aktion:** {cycle_result.action.value}
- **Schleife:** {cycle_result.loop_name.value}
- **Begründung:** {cycle_result.reasoning}
- **Pheromone im Feld:** {len(all_pheromones)}

## Pheromone

"""
    for p in all_pheromones[:20]:
        tags_str = ", ".join(p.tags) if p.tags else "(keine Tags)"
        report += f"- **{p.type.value}** ({p.source_agent}) [{tags_str}]: {p.content[:150]}...\n"

    report_path.write_text(report, encoding="utf-8")
    print(f"  ✓ Bericht: {report_path}")

    print("\n" + "=" * 70)
    print(f"✅ Test erfolgreich abgeschlossen in {elapsed:.2f}s!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

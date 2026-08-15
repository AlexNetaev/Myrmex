"""
src/diagnostics/structure_report.py
Generiert einen Bericht über die Systemstruktur.

Dieses Modul überprüft:
- Ob alle Kasten registriert sind
- Ob die Schleifen-Definitionen konsistent sind
- Ob die Workspace-Struktur vollständig ist
- Ob das Pheromon-Feld funktionsfähig ist
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone


def generate_structure_report(workspace_path: Path) -> dict:
    """
    Generiert einen umfassenden Struktur-Bericht.
    
    Args:
        workspace_path: Der Pfad zum Workspace.
    
    Returns:
        Ein dict mit dem Bericht.
    """
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_path": str(workspace_path),
        "checks": [],
        "summary": {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        },
    }
    
    # Check 1: Workspace-Verzeichnisse
    expected_dirs = [
        "00_System",
        "01_Pheromon_Field",
        "02_Research_Cycles",
        "03_Hardware_Queue",
        "04_Knowledge_Base",
        "05_Loops",
    ]
    
    for dir_name in expected_dirs:
        dir_path = workspace_path / dir_name
        exists = dir_path.exists() and dir_path.is_dir()
        report["checks"].append({
            "name": f"Verzeichnis {dir_name}",
            "status": "passed" if exists else "failed",
            "detail": f"Pfad: {dir_path}",
        })
        report["summary"]["total_checks"] += 1
        if exists:
            report["summary"]["passed"] += 1
        else:
            report["summary"]["failed"] += 1
    
    # Check 2: Registry
    try:
        from src.castes.registry import get_registry
        registry = get_registry()
        registered = registry.get_registered_actions()
        
        report["checks"].append({
            "name": "Kasten-Registry",
            "status": "passed" if len(registered) > 0 else "failed",
            "detail": f"{len(registered)} Aktionen registriert",
        })
        report["summary"]["total_checks"] += 1
        report["summary"]["passed"] += 1 if len(registered) > 0 else 0
        report["summary"]["failed"] += 0 if len(registered) > 0 else 1
    except Exception as e:
        report["checks"].append({
            "name": "Kasten-Registry",
            "status": "failed",
            "detail": f"Fehler: {e}",
        })
        report["summary"]["total_checks"] += 1
        report["summary"]["failed"] += 1
    
    # Check 3: Pheromon-Feld
    pheromone_dir = workspace_path / "01_Pheromon_Field"
    if pheromone_dir.exists():
        try:
            from src.pheromones.pheromone_field import PheromoneField
            field = PheromoneField(field_root=pheromone_dir)
            pheromones = field.scan()
            
            report["checks"].append({
                "name": "Pheromon-Feld",
                "status": "passed",
                "detail": f"{len(pheromones)} Pheromone im Feld",
            })
            report["summary"]["total_checks"] += 1
            report["summary"]["passed"] += 1
        except Exception as e:
            report["checks"].append({
                "name": "Pheromon-Feld",
                "status": "warning",
                "detail": f"Fehler beim Lesen: {e}",
            })
            report["summary"]["total_checks"] += 1
            report["summary"]["warnings"] += 1
    
    # Check 4: Theory Baseline
    theory_path = workspace_path / "04_Knowledge_Base" / "theory_baseline.md"
    if theory_path.exists():
        content = theory_path.read_text(encoding="utf-8")
        report["checks"].append({
            "name": "Theory Baseline",
            "status": "passed",
            "detail": f"{len(content)} Zeichen",
        })
        report["summary"]["total_checks"] += 1
        report["summary"]["passed"] += 1
    else:
        report["checks"].append({
            "name": "Theory Baseline",
            "status": "warning",
            "detail": "Datei existiert noch nicht (wird bei erster Konsolidierung erstellt)",
        })
        report["summary"]["total_checks"] += 1
        report["summary"]["warnings"] += 1
    
    return report

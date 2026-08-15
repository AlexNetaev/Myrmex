# 🐜 Myrmex: Emergent Research Architecture

**Version:** 1.0  
**Status:** Phase 1 abgeschlossen — Basis-Architektur + LLM-Integration  
**Datum:** 2026-08-15

---

## Vision

Myrmex ist eine **emergente Forschungsarchitektur** für autonome Labore. Sie basiert auf dem Ameisen-Prinzip (**Stigmergie**): Spezialisierte Agenten (Kasten) arbeiten über indirekte Kommunikation (Pheromone) zusammen und erzeugen komplexes wissenschaftliches Verhalten aus einfachen lokalen Regeln.

**Kernprinzip:** Wissenschaftliche Erkenntnis entsteht nicht durch zentrale Planung, sondern durch die Interaktion spezialisierter Agenten in einer geteilten Informationslandschaft.

---

## Die drei Schichten

```
┌─────────────────────────────────────────────────────┐
│ SCHICHT 3: DIE KÖNIGIN (Stratege-Ebene)             │
│ → Phase 2+ (noch nicht implementiert)               │
│ → Setzt übergeordnete Ziele, schreibt Paper         │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ SCHICHT 2: DER SCHWARM (Arbeiter-Ebene)             │
│ → 9 Kasten, 4 Schleifen, Arbiter als Kompass        │
│ → 4 Kasten mit LLM-Integration                      │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ SCHICHT 1: DAS PHEROMON-FELD (Informations-Layer)   │
│ → Spuren 🟢, Kristalle 💎, Warnungen 🔴             │
│ → Metadaten, Verdunstung, Verstärkung               │
└─────────────────────────────────────────────────────┘
```

---

## Die 9 Kasten

| Kaste | Rolle | LLM-Integration | ActionType |
|-------|-------|-----------------|------------|
| 🧠 **HypothesizerCaste** | Hypothesen generieren | ✅ HypothesisModel | HYPOTHESIZE |
| 🧪 **SimulatorCaste** | Digitaler Zwilling | ❌ (deterministisch) | SIMULATE |
| 📋 **PlannerCaste** | Experimente planen | ✅ PlanModel | PLAN |
| ⚙️ **ExecutorCaste** | Messung durchführen | ❌ (deterministisch) | MEASURE |
| 📊 **AnalystCaste** | Daten auswerten | ✅ AnalysisModel | ANALYZE |
| 📚 **TheoristCaste** | Wissen konsolidieren | ✅ ConsolidationModel | CONSOLIDATE |
| 🛡️ **GuardianCaste** | Wissen validieren | ❌ (deterministisch) | VALIDATE |
| 🗄️ **ArchivistCaste** | Wissen archivieren | ❌ (deterministisch) | ARCHIVE |
| ⚖️ **Arbiter** | Koordinieren | ❌ (deterministisch) | — |

### LLM-Konfiguration

- **Modell:** `gemma4:31b-cloud`
- **Host:** `http://localhost:11434` (Ollama)
- **Temperatur:** 0.2 (niedrig für strukturierte Ausgabe)
- **Max-Retries:** 3
- **Context-Size:** 4096

Alle LLM-Kasten haben einen **deterministischen Fallback**, falls das LLM nicht verfügbar ist.

---

## Die 4 Schleifen

| Schleife | Zweck | Aktions-Sequenz |
|----------|-------|-----------------|
| **A: Simulation** | Digitaler Zwilling kalibrieren | SIMULATE → ANALYZE |
| **B: Experiment** | Forschungs-Motor | PLAN → MEASURE → ANALYZE → HYPOTHESIZE |
| **C: Wissen** | Wissens-Aufbau | ANALYZE → CONSOLIDATE → VALIDATE → ARCHIVE |
| **D: Koordination** | Meta-Koordination | (vom Arbiter direkt gesteuert) |

---

## Installation

### Voraussetzungen

- Python 3.10+
- Ollama mit Modell `gemma4:31b-cloud` (für LLM-Kasten)
- pip

### Setup

```bash
# 1. Repository klonen
cd /workspace/myrmex

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Workspace initialisieren
python -c "
from src.workspace.workspace_manager import WorkspaceManager
WorkspaceManager().initialize()
print('✅ Workspace initialisiert')
"

# 4. Ollama starten (für LLM-Kasten)
ollama serve

# Modell laden (falls noch nicht geladen)
ollama pull gemma4:31b-cloud
```

---

## Verwendung

### Erster Test

```bash
# Vollständigen End-to-End-Test starten
python run_first_test.py
```

### Einzelne Zyklen ausführen

```python
from src.workspace.workspace_manager import WorkspaceManager
from src.arbiter.arbiter import Arbiter
from src.loops.loop_runner import LoopRunner

# Workspace initialisieren
wm = WorkspaceManager()
wm.initialize()

# Arbiter und LoopRunner erstellen
arbiter = Arbiter(workspace_path=wm.workspace_root)
loop_runner = LoopRunner(workspace_path=wm.workspace_root)

# Zyklus ausführen
result = arbiter.run_cycle(loop_runner)
print(f"Aktion: {result.action.value}")
print(f"Schleife: {result.loop_name.value}")
```

### Hardware-Dummy starten (separates Terminal)

```bash
cd /workspace/orbus_dummy_v2
python dummy_daemon.py
```

---

## Verzeichnisstruktur

```
myrmex/
├── config.py                     # Konfiguration (Pfade, Konstanten)
├── main.py                       # Haupt-Einstiegspunkt
├── run_first_test.py             # Erstes Test-Skript
├── requirements.txt              # Python-Dependencies
├── README.md                     # Diese Datei
├── PHASE1_STATUS_REPORT.md       # Status-Protokoll
├── hardware_profiles/
│   └── orbus_dummy_v2.yaml       # Hardware-Profil für den Dummy
├── myrmex_workspace/             # Workspace (wird erstellt)
│   ├── 00_System/                # Directive, Pläne, Konfiguration
│   ├── 01_Pheromon_Field/        # Pheromon-Feld
│   │   ├── trails/               # Flüchtige Pheromone
│   │   ├── crystals/             # Permanente Pheromone
│   │   └── warnings/             # Warn-Pheromone
│   ├── 02_Research_Cycles/       # Zyklus-Verzeichnisse
│   ├── 03_Hardware_Queue/        # Hardware-Queue
│   ├── 04_Knowledge_Base/        # theory_baseline.md, Archive
│   └── 05_Loops/                 # Schleifen-Zustände
├── src/
│   ├── arbiter/                  # Arbiter (Kompass)
│   ├── castes/                   # Die 9 Kasten
│   ├── diagnostics/              # Struktur-Berichte
│   ├── loops/                    # Schleifen-Definitionen + LoopRunner
│   ├── models/                   # Pydantic-Modelle
│   ├── pheromones/               # Pheromon-Feld-Manager
│   └── workspace/                # Workspace-Manager
└── tests/                        # ~310 Tests
```

---

## Tests

```bash
# Alle Tests ausführen
python -m pytest tests/ -v

# Nur Kasten-Tests
python -m pytest tests/test_*caste*.py tests/test_analyst*.py tests/test_hypothesizer*.py -v

# Nur LLM-Tests
python -m pytest tests/test_*_llm.py -v

# Nur Integrationstests
python -m pytest tests/test_integration.py tests/test_end_to_end.py -v
```

**Test-Statistik:** ~310 Tests in 29 Dateien

---

## Nächste Schritte (Phase 2+)

- ❌ Königin-Agent (LLM-Orchestrierung auf Stratege-Ebene)
- ❌ Paper-Zyklen und Zonierung
- ❌ Dashboard-Integration
- ❌ Echte Hardware-Anbindung (statt Dummy)
- ❌ Komplexe Physik-Modelle (statt einfacher Simulationen)
- ❌ Bayesian Optimization (statt OFAT)
- ❌ API-Dokumentation (Sphinx/ReadTheDocs)

---

## Lizenz

MIT
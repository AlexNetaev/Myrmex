# Myrmex-Architektur

Myrmex ist eine emergente Forschungsarchitektur für autonome Labore. Das System ist nach dem Vorbild eines Ameisenstaats organisiert, in dem spezialisierte "Kasten" zusammenarbeiten, um wissenschaftliche Experimente zu planen, durchzuführen und auszuwerten.

## Die drei Schichten

### 1. Pheromon-Feld (Schicht 1)

Das Pheromon-Feld ist das zentrale Kommunikationsmedium des Systems. Es ermöglicht indirekte Kommunikation zwischen den Kasten über flüchtige Signale (Pheromone).

- **PheromoneType.TRAIL**: Flüchtige Spuren, die von Kasten hinterlassen werden
- **PheromoneType.CRYSTAL**: Permanente, kristallisierte Erkenntnisse
- **PheromoneType.WARNING**: Warnsignale bei Problemen

Das Feld verdunstet Pheromone automatisch, wodurch veraltete Informationen verschwinden. Starke Pheromone können zu Kristallen werden.

### 2. Kasten (Schicht 2)

Die 9 Kasten sind die "Arbeiter" des Schwarms. Jede Kaste hat eine spezifische Rolle:

| Kaste | Aktion | Rolle |
|-------|--------|-------|
| **AnalystCaste** | ANALYZE | Analysiert experimentelle Daten und extrahiert Muster |
| **PlannerCaste** | PLAN | Plant Experimente mit OFAT-Methode oder LLM-basiert |
| **ExecutorCaste** | MEASURE | Führt Experimente durch, schreibt Hardware-Queue |
| **SimulatorCaste** | SIMULATE | Simuliert Experimente virtuell |
| **TheoristCaste** | CONSOLIDATE | Konsolidiert Erkenntnisse in die theory_baseline.md |
| **GuardianCaste** | VALIDATE | Validiert die theory_baseline.md auf Plausibilität |
| **ArchivistCaste** | ARCHIVE | Komprimiert und archiviert Wissen |
| **HypothesizerCaste** | HYPOTHESIZE | Generiert neue Hypothesen |
| **Arbiter** | — | Koordiniert den Schwarm (der "Kompass") |

Alle Kasten erben von `BaseCaste` und implementieren:
- `caste_name`: Eindeutiger Name der Kaste
- `role`: Beschreibung der Rolle
- `specialization`: Spezialisierung der Kaste
- `reads_pheromones`: Liste der erlaubten Pheromon-Typen zum Lesen
- `writes_pheromones`: Liste der erlaubten Pheromon-Typen zum Schreiben
- `execute(work_dir)`: Die Hauptausführungsmethode

### 3. Arbiter (Schicht 3)

Der Arbiter ist die Orchestrierungs-Komponente, die keine eigene Kaste ist, sondern Entscheidungen trifft:

- Liest die aktuelle Landschaft (Pheromon-Feld, Theorie, Ziele)
- Trifft Entscheidungen basierend auf Heuristiken
- Erstellt einen Plan mit Loop-Prioritäten

## Die vier Schleifen

Myrmex operiert in vier verschiedenen Schleifen, die jeweils unterschiedliche Aktionen ausführen:

| Schleife | Name | Aktionen | Energie |
|----------|------|----------|---------|
| **LOOP_A** | Simulation | SIMULATE → ANALYZE | -5 pro Iteration |
| **LOOP_B** | Experiment | PLAN → MEASURE → ANALYZE → HYPOTHESIZE | +20 pro MEASURE |
| **LOOP_C** | Knowledge | ANALYZE → CONSOLIDATE → VALIDATE → ARCHIVE | -10 pro Iteration |
| **LOOP_D** | Coordination | (vom Arbiter direkt gesteuert) | Variabel |

## CasteRegistry

Die `CasteRegistry` ist das zentrale Mapping zwischen `ActionType` und Kasten-Klasse:

```python
registry = get_registry()
caste_class = registry.get_caste_for_action(ActionType.ANALYZE)
caste = caste_class(workspace_path=some_path)
result = caste.execute(work_dir=some_dir)
```

Die Registry unterstützt:
- Registrierung neuer Kasten mit `register(action_type, caste_class)`
- Zurücksetzen für Tests mit `reset_registry()`
- Prüfung auf Placeholder mit `is_placeholder(action_type)`

## Workspace-Struktur

```
workspace/
├── 00_System/           # Directive, Arbiter-Plan, Shadow Memory
├── 01_Pheromon_Field/   # Pheromon-Dateien (trails/, crystals/, warnings/)
├── 02_Research_Cycles/  # Cycle-Ordner mit Ergebnissen
├── 03_Hardware_Queue/   # experiment.json für Hardware
├── 04_Knowledge_Base/   # theory_baseline.md
└── 05_Loops/            # Loop-Zustände
```

## Design-Prinzipien

1. **Emergenz**: Intelligenz entsteht aus der Interaktion einfacher Komponenten
2. **Indirekte Kommunikation**: Kasten kommunizieren über Pheromone, nicht direkt
3. **Trennung von Concerns**: TheoristCaste schreibt, GuardianCaste prüft
4. **Determinismus vor LLM**: Phase 1 verwendet deterministische Logik, LLM kommt später
5. **Shadow Memory**: Jede Kasten-Ausführung wird protokolliert für Audit-Trails

---

## LLM-Integration (Phase 1.5)

In Phase 1.5 wurde die LLM-Integration in 4 Kasten implementiert:

### Kasten mit LLM

| Kaste | Pydantic-Modell | Zweck |
|-------|-----------------|-------|
| **HypothesizerCaste** | `HypothesisModel` | Echte Hypothesen generieren |
| **AnalystCaste** | `AnalysisModel` | Daten wissenschaftlich interpretieren |
| **TheoristCaste** | `ConsolidationModel` | Wissen konsolidieren + Widersprüche auflösen |
| **PlannerCaste** | `PlanModel` | Strategische Experiment-Planung |

### LLM-Konfiguration

- **Modell:** `gemma4:31b-cloud`
- **Host:** `http://localhost:11434` (Ollama)
- **Temperatur:** 0.2
- **Max-Retries:** 3
- **Context-Size:** 4096

### Design-Prinzip

Alle LLM-Kasten haben einen **deterministischen Fallback**:
1. Versuche den LLM-Aufruf
2. Falls der LLM-Aufruf fehlschlägt (Timeout, Invalid JSON, etc.): Verwende den deterministischen Fallback
3. Schreibe das Ergebnis in `extra_data` (`llm_used: true/false`)

Dies stellt sicher, dass das System auch ohne LLM funktionsfähig bleibt.

### Neue Test-Dateien

- `tests/test_hypothesizer_llm.py` (4 Tests)
- `tests/test_analyst_llm.py` (6 Tests)
- `tests/test_theorist_llm.py` (6 Tests)
- `tests/test_planner_llm.py` (7 Tests)

**Gesamt:** 23 neue Tests für LLM-Integration

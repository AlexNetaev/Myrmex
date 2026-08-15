# Myrmex

Eine emergente Forschungsarchitektur für autonome Labore, inspiriert vom Ameisen-Prinzip (Stigmergie).

## Architektur

Myrmex besteht aus drei Schichten:

1. **Schicht 1: Das Pheromon-Feld** - Informations-Layer (Spuren, Kristalle, Warnungen)
2. **Schicht 2: Der Schwarm** - 9 Kasten (Agenten), 4 Schleifen, Arbiter
3. **Schicht 3: Die Königin** - Stratege-Ebene (Phase 2+)

## Die 9 Kasten

| Kaste | Rolle |
|-------|-------|
| Hypothesizer | Hypothesen generieren |
| Simulator | Digitaler Zwilling |
| Planner | Experimente planen |
| Executor | Messung durchführen |
| Analyst | Daten auswerten |
| Theorist | Theorie pflegen |
| Guardian | Validieren & Sichern |
| Archivist | Wissen verwalten |
| Arbiter | Koordinieren (der "Kompass") |

## Die 4 Schleifen

| Schleife | Zweck |
|----------|-------|
| Loop A | Simulations-Kalibrierung |
| Loop B | Experiment-Iteration |
| Loop C | Wissens-Aufbau |
| Loop D | Meta-Koordination |

## Die 3 Pheromon-Typen

| Typ | Symbol | Bedeutung | Verdunstung |
|-----|--------|-----------|-------------|
| Trail | 🟢 | Flüchtige Information | Verdunstet über Zeit |
| Crystal | 💎 | Gesicherte Erkenntnis | Verdunstet nie |
| Warning | 🔴 | Negatives Signal | Verdunstet langsam |

## Installation

```bash
pip install -r requirements.txt
```

## Workspace-Struktur

Der Workspace ist das dateibasierte Gedächtnis von Myrmex:

```
myrmex_workspace/
├── 00_System/           # Directive, Target Crystal, Arbiter Plan
├── 01_Pheromon_Field/   # Trails, Crystals, Warnings
├── 02_Research_Cycles/  # Forschungszyklen
├── 03_Hardware_Queue/   # Hardware-Jobs
├── 04_Knowledge_Base/   # Theorie und Fakten
└── 05_Loops/            # Schleifen-Status
```

## Entwicklung

Dies ist Phase 0 des Projekts - nur das Fundament (Datenstrukturen) ist implementiert.
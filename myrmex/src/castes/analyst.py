"""
src/castes/analyst.py
Die Analyst-Kaste — wertet Messdaten aus und schreibt Erkenntnisse als Pheromone.

In Phase 1 macht der Analyst deterministische Analyse (Statistik, Plateau-Erkennung).
Keine LLM-Aufrufe — die kommen in späteren Phasen.

Typische Aufgaben:
- Messdaten aus CSV-Dateien lesen (measurement.csv, sim_data.csv)
- Statistische Kennzahlen berechnen (Plateau, Slope, AUC, Min/Max/Mean)
- Analyse-Ergebnisse als TRAIL-Pheromone ins Feld schreiben
- Detaillierte Ergebnisse als JSON-Datei speichern
"""
from __future__ import annotations
import csv
import json
import logging
from pathlib import Path
from typing import Any

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType


class AnalystCaste(BaseCaste):
    """
    Die Analyst-Kaste — wertet Messdaten aus und schreibt Erkenntnisse.
    
    In Phase 1: Deterministische Analyse (Statistik, Plateau-Erkennung).
    Keine LLM-Aufrufe.
    """
    
    caste_name = CasteName.ANALYST
    role = "Daten auswerten und Erkenntnisse extrahieren"
    specialization = "Statistische Analyse von Zeitreihen-Daten"
    reads_pheromones = []  # Liest nur Dateien, keine Pheromone
    writes_pheromones = [PheromoneType.TRAIL]  # Schreibt Analyse-Erkenntnisse
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Analyse aus:
        1. Sucht nach CSV-Dateien im work_dir (measurement.csv, sim_data.csv)
        2. Analysiert jede gefundene CSV-Datei
        3. Schreibt Analyse-Ergebnisse als JSON
        4. Schreibt ein TRAIL-Pheromon mit den Erkenntnissen
        """
        self.logger.info("[%s] Starting analysis in %s", self.caste_name.value, work_dir)
        
        # 1. CSV-Dateien finden
        csv_files = self._find_csv_files(work_dir)
        self.logger.info("[%s] Found %d CSV file(s): %s", 
                        self.caste_name.value, len(csv_files), 
                        [f.name for f in csv_files])
        
        if not csv_files:
            self.logger.warning("[%s] No CSV files found in %s", 
                              self.caste_name.value, work_dir)
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={"reason": "no_csv_files_found"},
            )
        
        # 2. Jede CSV-Datei analysieren
        all_analyses: dict[str, dict] = {}
        output_files: list[str] = []
        
        for csv_file in csv_files:
            analysis = self._analyze_csv_file(csv_file)
            all_analyses[csv_file.name] = analysis
            
            # 3. Analyse-Ergebnis als JSON schreiben
            result_filename = f"{csv_file.stem}_analysis.json"
            result_path = work_dir / result_filename
            result_path.write_text(
                json.dumps(analysis, indent=2), 
                encoding="utf-8"
            )
            output_files.append(result_filename)
            self.logger.info("[%s] Wrote analysis to %s", 
                           self.caste_name.value, result_path)
        
        # 4. TRAIL-Pheromon mit Zusammenfassung schreiben
        summary = self._build_analysis_summary(all_analyses)
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=summary,
            tags=["analysis", "measurement"],
            strength=0.6,
            relevance=0.7,
        )
        
        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=0,
            pheromones_written=1,
            output_files=output_files,
            extra_data={
                "csv_files_analyzed": [f.name for f in csv_files],
                "analyses": all_analyses,
                "pheromone_id": pheromone.id,
            },
        )
    
    def _find_csv_files(self, work_dir: Path) -> list[Path]:
        """
        Sucht nach CSV-Dateien im work_dir.
        Priorisiert: measurement.csv, sim_data.csv, dann alle anderen .csv
        """
        if not work_dir.exists():
            return []
        
        # Priorisierte Dateien
        priority_names = ["measurement.csv", "sim_data.csv"]
        priority_files = [work_dir / name for name in priority_names if (work_dir / name).exists()]
        
        # Alle anderen CSV-Dateien
        all_csv = sorted(work_dir.glob("*.csv"))
        other_csv = [f for f in all_csv if f.name not in priority_names]
        
        return priority_files + other_csv
    
    def _analyze_csv_file(self, csv_path: Path) -> dict[str, Any]:
        """
        Analysiert eine einzelne CSV-Datei und gibt statistische Kennzahlen zurück.
        """
        try:
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as exc:
            self.logger.error("[%s] Failed to read %s: %s", 
                            self.caste_name.value, csv_path.name, exc)
            return {"error": str(exc), "file": csv_path.name}
        
        if not rows:
            return {"error": "empty_file", "file": csv_path.name, "row_count": 0}
        
        # Header extrahieren
        headers = list(rows[0].keys())
        
        # Alle numerischen Spalten identifizieren
        numeric_columns = self._find_numeric_columns(rows, headers)
        
        # Statistik pro numerischer Spalte
        column_stats: dict[str, dict] = {}
        for col in numeric_columns:
            values = self._extract_numeric_values(rows, col)
            if values:
                column_stats[col] = self._compute_statistics(values)
        
        # Zeit-Spalte erkennen (time_ms, time_s, timestamp, etc.)
        time_column = self._find_time_column(headers)
        
        # Plateau-Erkennung (für die letzte numerische Spalte)
        plateau_analysis = None
        if numeric_columns and len(rows) >= 10:
            last_numeric_col = numeric_columns[-1]
            values = self._extract_numeric_values(rows, last_numeric_col)
            plateau_analysis = self._detect_plateau(values)
        
        return {
            "file": csv_path.name,
            "row_count": len(rows),
            "column_count": len(headers),
            "headers": headers,
            "numeric_columns": numeric_columns,
            "time_column": time_column,
            "column_statistics": column_stats,
            "plateau_analysis": plateau_analysis,
        }
    
    def _find_numeric_columns(self, rows: list[dict], headers: list[str]) -> list[str]:
        """Identifiziert alle Spalten, die numerische Werte enthalten."""
        numeric_cols = []
        if not rows:
            return numeric_cols
        
        first_row = rows[0]
        for header in headers:
            try:
                float(first_row[header])
                numeric_cols.append(header)
            except (ValueError, TypeError):
                continue
        
        return numeric_cols
    
    def _extract_numeric_values(self, rows: list[dict], column: str) -> list[float]:
        """Extrahiert alle numerischen Werte aus einer Spalte."""
        values = []
        for row in rows:
            try:
                val = float(row[column])
                values.append(val)
            except (ValueError, TypeError, KeyError):
                continue
        return values
    
    def _compute_statistics(self, values: list[float]) -> dict[str, float]:
        """Berechnet statistische Kennzahlen für eine Liste von Werten."""
        if not values:
            return {}
        
        n = len(values)
        sorted_vals = sorted(values)
        mean_val = sum(values) / n
        variance = sum((x - mean_val) ** 2 for x in values) / n
        std_dev = variance ** 0.5
        
        # Area Under Curve (einfache Trapez-Regel)
        auc = sum(values)  # Vereinfacht: Summe der Werte
        
        return {
            "count": n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": round(mean_val, 4),
            "std_dev": round(std_dev, 4),
            "median": round(sorted_vals[n // 2], 4),
            "auc": round(auc, 4),
        }
    
    def _find_time_column(self, headers: list[str]) -> str | None:
        """Erkennt die Zeit-Spalte (time_ms, time_s, timestamp, etc.)."""
        time_keywords = ["time_ms", "time_s", "timestamp", "time", "t"]
        for header in headers:
            if header.lower() in time_keywords:
                return header
        return None
    
    def _detect_plateau(self, values: list[float], tail_fraction: float = 0.2) -> dict[str, Any]:
        """
        Erkennt, ob die Werte ein Plateau (Steady State) erreichen.
        Prüft die letzten `tail_fraction` der Werte auf geringe Varianz.
        """
        if len(values) < 10:
            return {"detected": False, "reason": "too_few_values"}
        
        tail_size = max(1, int(len(values) * tail_fraction))
        tail_values = values[-tail_size:]
        
        mean_val = sum(tail_values) / len(tail_values)
        variance = sum((x - mean_val) ** 2 for x in tail_values) / len(tail_values)
        std_dev = variance ** 0.5
        
        # Plateau erkannt, wenn Standardabweichung < 5% des Mittelwerts
        threshold = abs(mean_val) * 0.05 if mean_val != 0 else 1.0
        is_plateau = std_dev < threshold
        
        # Slope der letzten Werte (lineare Regression vereinfacht)
        slope = self._estimate_slope(tail_values)
        
        return {
            "detected": is_plateau,
            "tail_size": tail_size,
            "tail_mean": round(mean_val, 4),
            "tail_std_dev": round(std_dev, 4),
            "tail_slope": round(slope, 6),
            "threshold": round(threshold, 4),
        }
    
    def _estimate_slope(self, values: list[float]) -> float:
        """Schätzt die Steigung der letzten Werte (vereinfachte lineare Regression)."""
        n = len(values)
        if n < 2:
            return 0.0
        
        # Einfache Steigung: (letzter - erster) / n
        return (values[-1] - values[0]) / n
    
    def _build_analysis_summary(self, all_analyses: dict[str, dict]) -> str:
        """
        Baut eine zusammenfassende Beschreibung der Analyse für das Pheromon.
        """
        parts = []
        for filename, analysis in all_analyses.items():
            if "error" in analysis:
                parts.append(f"{filename}: Error - {analysis['error']}")
                continue
            
            row_count = analysis.get("row_count", 0)
            plateau = analysis.get("plateau_analysis")
            
            summary_line = f"{filename}: {row_count} rows"
            if plateau and plateau.get("detected"):
                tail_mean = plateau.get("tail_mean", "?")
                summary_line += f", plateau detected (mean={tail_mean})"
            elif plateau:
                summary_line += ", no plateau"
            
            parts.append(summary_line)
        
        return " | ".join(parts)

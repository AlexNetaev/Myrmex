"""
src/castes/analyst.py
Die Analyst-Kaste — wertet Messdaten aus und schreibt Erkenntnisse als Pheromone.

In dieser Version nutzt sie ein LLM für die wissenschaftliche Interpretation.
Die deterministische Logik bleibt als Fallback und Daten-Vorverarbeitung erhalten.

Typische Aufgaben:
- Messdaten aus CSV-Dateien lesen (measurement.csv, sim_data.csv)
- Statistische Kennzahlen berechnen (Plateau, Slope, AUC, Min/Max/Mean)
- LLM-basierte wissenschaftliche Interpretation der Daten
- Analyse-Ergebnisse als TRAIL-Pheromone ins Feld schreiben
"""
from __future__ import annotations
import csv
import logging
from pathlib import Path
from typing import Any

from src.castes.base_caste import BaseCaste, CasteExecutionResult
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType
from src.castes.analysis_models import AnalysisModel, AnalysisFinding


logger = logging.getLogger("caste.analyst")

# LLM-Konfiguration (identisch zu HypothesizerCaste)
OLLAMA_MODEL = "gemma4:31b-cloud"
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_CONTEXT_SIZE = 4096


class AnalystCaste(BaseCaste):
    """
    Die Analyst-Kaste — wertet Messdaten aus und schreibt Erkenntnisse.

    In dieser Version: LLM-basierte wissenschaftliche Interpretation mit
    deterministischem Fallback und Daten-Vorverarbeitung.
    """
    
    caste_name = CasteName.ANALYST
    role = "Daten auswerten und Erkenntnisse extrahieren"
    specialization = "LLM-basierte Dateninterpretation mit deterministischem Fallback"
    reads_pheromones = []  # Liest nur Dateien, keine Pheromone
    writes_pheromones = [PheromoneType.TRAIL]  # Schreibt Analyse-Erkenntnisse
    
    MEASUREMENT_CSV_FILENAME = "measurement.csv"
    SIM_DATA_CSV_FILENAME = "sim_data.csv"
    
    def execute(self, work_dir: Path) -> CasteExecutionResult:
        """
        Führt die Analyse aus:
        1. Liest measurement.csv und sim_data.csv.
        2. Berechnet deterministische Kennzahlen (Statistik, Diskrepanzen).
        3. Versucht die LLM-basierte Interpretation.
        4. Falls LLM fehlschlägt: Verwendet deterministischen Fallback.
        5. Schreibt ein TRAIL-Pheromon mit der Analyse.
        """
        self.logger.info("[%s] Starting analysis", self.caste_name.value)

        # 1. Daten laden
        measurement_path = work_dir / "B_Hardware" / self.MEASUREMENT_CSV_FILENAME
        simulation_path = work_dir / "A_Simulation" / self.SIM_DATA_CSV_FILENAME
        
        measurement_data = self._load_csv(measurement_path)
        simulation_data = self._load_csv(simulation_path)

        if not measurement_data:
            self.logger.info("[%s] No measurement data to analyze", self.caste_name.value)
            return CasteExecutionResult(
                caste_name=self.caste_name,
                success=True,
                pheromones_read=0,
                pheromones_written=0,
                output_files=[],
                extra_data={"reason": "no_measurement_data"},
            )

        # 2. Deterministische Kennzahlen berechnen (Vorverarbeitung für LLM)
        stats = self._compute_statistics(measurement_data, simulation_data)

        # 3. LLM-basierte Interpretation versuchen
        analysis = None
        llm_used = False
        try:
            analysis = self._analyze_with_llm(measurement_data, simulation_data, stats)
            llm_used = True
            self.logger.info("[%s] LLM-based analysis completed successfully", self.caste_name.value)
        except Exception as e:
            self.logger.warning(
                "[%s] LLM-based analysis failed: %s. Falling back to deterministic logic.",
                self.caste_name.value, e,
            )

        # 4. Fallback: Deterministische Analyse
        if analysis is None:
            analysis = self._analyze_deterministic(measurement_data, simulation_data, stats)
            llm_used = False

        # 5. TRAIL-Pheromon schreiben
        finding_categories = [f["category"] for f in analysis.get("key_findings", [])]
        pheromone = self.write_pheromone(
            pheromone_type=PheromoneType.TRAIL,
            content=analysis["summary"],
            tags=["analysis", "findings"] + finding_categories,
            strength=0.6,
            relevance=0.8,
        )

        return CasteExecutionResult(
            caste_name=self.caste_name,
            success=True,
            pheromones_read=0,
            pheromones_written=1,
            output_files=[],
            extra_data={
                "llm_used": llm_used,
                "confidence": analysis.get("confidence", "unknown"),
                "num_findings": len(analysis.get("key_findings", [])),
                "pheromone_id": pheromone.id,
                "statistics": stats,
            },
        )

    def _load_csv(self, csv_path: Path) -> list[dict]:
        """Lädt eine CSV-Datei als Liste von Dictionaries."""
        if not csv_path.exists():
            self.logger.info("[%s] CSV not found: %s", self.caste_name.value, csv_path)
            return []

        try:
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            self.logger.warning("[%s] Failed to read CSV %s: %s", self.caste_name.value, csv_path, e)
            return []

    def _compute_statistics(self, measurement: list[dict], simulation: list[dict]) -> dict:
        """
        Berechnet deterministische Kennzahlen als Vorverarbeitung für das LLM.
        Diese Zahlen sind die "Fakten", die das LLM interpretieren soll.
        """
        stats: dict = {
            "measurement_points": len(measurement),
            "simulation_points": len(simulation),
            "has_simulation": len(simulation) > 0,
        }

        # Fluoreszenz-Statistik (Messung)
        if measurement and "fluorescence_au" in measurement[0]:
            try:
                fluor_values = [float(r.get("fluorescence_au", 0)) for r in measurement]
                stats["meas_fluor_start"] = fluor_values[0]
                stats["meas_fluor_end"] = fluor_values[-1]
                stats["meas_fluor_min"] = min(fluor_values)
                stats["meas_fluor_max"] = max(fluor_values)
                stats["meas_fluor_mean"] = sum(fluor_values) / len(fluor_values)
                stats["meas_fluor_delta"] = fluor_values[-1] - fluor_values[0]
            except (ValueError, TypeError):
                pass

        # Temperatur-Statistik (Messung)
        if measurement and "temp_c" in measurement[0]:
            try:
                temp_values = [float(r.get("temp_c", 0)) for r in measurement]
                stats["meas_temp_start"] = temp_values[0]
                stats["meas_temp_end"] = temp_values[-1]
                stats["meas_temp_mean"] = sum(temp_values) / len(temp_values)
            except (ValueError, TypeError):
                pass

        # Fluoreszenz-Statistik (Simulation)
        if simulation and "fluorescence_au" in simulation[0]:
            try:
                sim_fluor_values = [float(r.get("fluorescence_au", 0)) for r in simulation]
                stats["sim_fluor_start"] = sim_fluor_values[0]
                stats["sim_fluor_end"] = sim_fluor_values[-1]
                stats["sim_fluor_delta"] = sim_fluor_values[-1] - sim_fluor_values[0]
            except (ValueError, TypeError):
                pass

        # Diskrepanz zwischen Simulation und Realität
        if "meas_fluor_delta" in stats and "sim_fluor_delta" in stats:
            stats["discrepancy_delta"] = stats["meas_fluor_delta"] - stats["sim_fluor_delta"]
            if stats["sim_fluor_delta"] != 0:
                stats["discrepancy_percent"] = (
                    stats["discrepancy_delta"] / abs(stats["sim_fluor_delta"]) * 100.0
                )

        return stats

    def _analyze_with_llm(
        self,
        measurement: list[dict],
        simulation: list[dict],
        stats: dict,
    ) -> dict:
        """
        Führt die LLM-basierte Datenanalyse durch.
        """
        # Daten kompakt darstellen (nur erste/letzte 5 Punkte + Statistik)
        meas_sample = self._format_sample(measurement, max_points=5)
        sim_sample = self._format_sample(simulation, max_points=5) if simulation else "(no simulation data)"
        stats_text = "\n".join(f"  {k}: {v}" for k, v in stats.items())

        prompt = f"""You are the Data Analyst for an autonomous self-driving laboratory.
Your task is to interpret experimental data and extract scientifically meaningful findings.

## Experimental Context
The experiment studies the Fenton reaction with fluorescein as a pH-sensitive fluorophore.
- Fluorescein fluorescence DECREASES as pH drops (protonation quenches fluorescence).
- The Fenton reaction generates H+ ions, causing pH to drop over time.
- Temperature accelerates the reaction kinetics.

## Measurement Data (Reality)
First/last 5 data points:
{meas_sample}

## Simulation Data (Digital Twin Prediction)
First/last 5 data points:
{sim_sample}

## Precomputed Statistics
{stats_text}

## Your Task
Analyze the data and provide:
1. A short summary (max. 300 characters).
2. A list of key findings (each with category and significance).
   Categories: 'discrepancy', 'anomaly', 'plateau', 'trend', 'confirmation'
   Significance: 'high', 'medium', 'low'
3. A scientific interpretation explaining WHY the observed patterns occur,
   based on Fenton chemistry and fluorescein photophysics.
4. A specific recommendation for the next experiment (which parameter to adjust and how).
5. Your confidence level ('high', 'medium', 'low').

Be specific, quantitative, and scientifically rigorous. Avoid vague statements.
"""

        system_prompt = (
            "You are the Data Analyst for an autonomous self-driving laboratory "
            "specializing in Fenton reaction kinetics and fluorescein photophysics. "
            "You interpret experimental data with scientific rigor, identifying "
            "discrepancies between simulation and reality, and providing actionable "
            "recommendations for the next experiment."
        )

        # LLM aufrufen
        result = self.ask_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            response_model=AnalysisModel,
            max_retries=DEFAULT_MAX_RETRIES,
            temperature=DEFAULT_TEMPERATURE,
            context_size=DEFAULT_CONTEXT_SIZE,
        )

        # In dict umwandeln
        return {
            "summary": result.summary,
            "key_findings": [f.model_dump() for f in result.key_findings],
            "scientific_interpretation": result.scientific_interpretation,
            "recommended_next_steps": result.recommended_next_steps,
            "confidence": result.confidence,
        }

    def _analyze_deterministic(
        self,
        measurement: list[dict],
        simulation: list[dict],
        stats: dict,
    ) -> dict:
        """
        Deterministischer Fallback für die Datenanalyse.
        Nutzt einfache Heuristiken, um Erkenntnisse zu extrahieren.
        """
        findings: list[dict] = []

        # Check 1: Fluoreszenz-Diskrepanz
        if "discrepancy_percent" in stats:
            disc = stats["discrepancy_percent"]
            if abs(disc) > 20:
                findings.append({
                    "description": (
                        f"Fluorescence delta discrepancy of {disc:.1f}% between "
                        f"simulation ({stats.get('sim_fluor_delta', 0):.2f}) and "
                        f"measurement ({stats.get('meas_fluor_delta', 0):.2f})."
                    ),
                    "category": "discrepancy",
                    "significance": "high" if abs(disc) > 50 else "medium",
                })
            else:
                findings.append({
                    "description": (
                        f"Fluorescence delta matches simulation within {abs(disc):.1f}%."
                    ),
                    "category": "confirmation",
                    "significance": "medium",
                })

        # Check 2: Plateau-Erkennung
        if "meas_fluor_delta" in stats and abs(stats["meas_fluor_delta"]) < 1.0:
            findings.append({
                "description": (
                    f"Fluorescence plateau detected (delta = {stats['meas_fluor_delta']:.2f} a.u.). "
                    f"System may have reached equilibrium."
                ),
                "category": "plateau",
                "significance": "high",
            })

        # Check 3: Starker Trend
        if "meas_fluor_delta" in stats and abs(stats["meas_fluor_delta"]) > 20:
            direction = "decrease" if stats["meas_fluor_delta"] < 0 else "increase"
            findings.append({
                "description": (
                    f"Strong fluorescence {direction} of {abs(stats['meas_fluor_delta']):.2f} a.u. "
                    f"over the measurement period."
                ),
                "category": "trend",
                "significance": "high",
            })

        # Fallback: Immer mindestens ein Finding
        if not findings:
            findings.append({
                "description": (
                    f"Analyzed {stats['measurement_points']} measurement points. "
                    f"No significant patterns detected."
                ),
                "category": "confirmation",
                "significance": "low",
            })

        # Zusammenfassung
        high_sig = sum(1 for f in findings if f["significance"] == "high")
        if high_sig > 0:
            confidence = "medium"
        else:
            confidence = "low"

        summary = (
            f"Analyzed {stats['measurement_points']} points: "
            f"{len(findings)} findings ({high_sig} high significance). "
            f"Primary: {findings[0]['description'][:150]}..."
        )

        return {
            "summary": summary,
            "key_findings": findings,
            "scientific_interpretation": "(deterministic fallback — no LLM interpretation available)",
            "recommended_next_steps": "Repeat experiment or adjust one parameter to test sensitivity.",
            "confidence": confidence,
        }

    def _format_sample(self, data: list[dict], max_points: int = 5) -> str:
        """Formatiert eine Daten-Stichprobe für den LLM-Prompt."""
        if not data:
            return "(no data)"

        if len(data) <= max_points * 2:
            # Kleine Datei: alle Zeilen
            lines = [", ".join(f"{k}={v}" for k, v in row.items()) for row in data]
            return "\n".join(lines)

        # Große Datei: erste und letzte max_points
        first = data[:max_points]
        last = data[-max_points:]
        lines = [", ".join(f"{k}={v}" for k, v in row.items()) for row in first]
        lines.append(f"... ({len(data) - 2 * max_points} points omitted) ...")
        lines.extend([", ".join(f"{k}={v}" for k, v in row.items()) for row in last])
        return "\n".join(lines)

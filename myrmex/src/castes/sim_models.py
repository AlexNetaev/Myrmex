"""
src/castes/sim_models.py
Deterministische physikalische Modelle für den digitalen Zwilling.

Diese Module erzeugen eine simulierte Zeitreihe, die dem Verhalten des
echten Experiments ähnelt. Sie sind rein deterministisch (kein LLM, kein
Zufall), damit die SimulatorCaste schnell, günstig und testbar ist.

Die Modelle sind bewusst einfach gehalten — sie müssen nicht perfekt sein,
nur physikalisch plausibel. Der Zweck ist, eine Vorhersage zu erzeugen,
gegen die der Analyst die echten Messdaten vergleichen kann.
"""
from __future__ import annotations
import math


def simulate_temperature(
    t_s: float,
    target_temp_c: float,
    ambient_temp_c: float = 22.0,
    tau_s: float = 10.0,
) -> float:
    """
    Simuliert die Temperatur als exponentielle Annäherung an das Ziel.
    
    T(t) = target + (ambient - target) * exp(-t / tau)
    
    Args:
        t_s: Zeit in Sekunden.
        target_temp_c: Zieltemperatur in °C.
        ambient_temp_c: Umgebungstemperatur in °C (Start-Wert).
        tau_s: Zeitkonstante der Aufheizung in Sekunden.
    
    Returns:
        Die simulierte Temperatur in °C.
    """
    return target_temp_c + (ambient_temp_c - target_temp_c) * math.exp(-t_s / tau_s)


def simulate_ph(
    t_s: float,
    ph_start: float = 7.4,
    delta_ph: float = 2.0,
    k_ph: float = 0.05,
) -> float:
    """
    Simuliert den pH-Wert, der über die Zeit sinkt (durch die Fenton-Reaktion).
    
    pH(t) = ph_start - delta_ph * (1 - exp(-k_ph * t))
    
    Args:
        t_s: Zeit in Sekunden.
        ph_start: Start-pH (typisch 7.4).
        delta_ph: Maximale pH-Absenkung (typisch 2.0).
        k_ph: Rate der pH-Absenkung in 1/s.
    
    Returns:
        Der simulierte pH-Wert.
    """
    return ph_start - delta_ph * (1.0 - math.exp(-k_ph * t_s))


def simulate_fluorescence(
    ph: float,
    pka: float = 6.4,
    fluor_conc_um: float = 10.0,
    f_max: float = 100.0,
) -> float:
    """
    Simuliert die Fluoreszenz basierend auf dem pH-Wert (Henderson-Hasselbalch).
    
    Die Fluoreszenz ist proportional zum Anteil der deprotonierten Form des
    Fluorophors. Bei hohem pH (über pKa) ist die Fluoreszenz hoch, bei
    niedrigem pH (unter pKa) ist sie niedrig.
    
    F = f_max * (conc_factor) * (ratio / (1 + ratio))
    wobei ratio = 10^(pH - pKa)
    
    Args:
        ph: Der aktuelle pH-Wert.
        pka: Der pKa-Wert des Fluorophors (typisch 6.4 für Fluorescein).
        fluor_conc_um: Die Fluorophor-Konzentration in µM (skaliert die Amplitude).
        f_max: Die maximale Fluoreszenz-Amplitude (bei voller Deprotonierung).
    
    Returns:
        Die simulierte Fluoreszenz in willkürlichen Einheiten (a.u.).
    """
    ratio = 10.0 ** (ph - pka)
    deprotonated_fraction = ratio / (1.0 + ratio)
    # Konzentration skaliert die Amplitude (linear, vereinfacht)
    conc_factor = min(fluor_conc_um / 10.0, 2.0)  # gekappt bei 2x
    return f_max * conc_factor * deprotonated_fraction


def generate_time_series(
    duration_s: float,
    interval_ms: int,
    target_temp_c: float,
    ph_start: float = 7.4,
    delta_ph: float = 2.0,
    k_ph: float = 0.05,
    pka: float = 6.4,
    fluor_conc_um: float = 10.0,
) -> list[dict]:
    """
    Erzeugt die vollständige simulierte Zeitreihe.
    
    Args:
        duration_s: Gesamtdauer der Simulation in Sekunden.
        interval_ms: Zeitintervall zwischen den Messpunkten in Millisekunden.
        target_temp_c: Zieltemperatur in °C.
        ph_start: Start-pH.
        delta_ph: Maximale pH-Absenkung.
        k_ph: Rate der pH-Absenkung.
        pka: pKa-Wert des Fluorophors.
        fluor_conc_um: Fluorophor-Konzentration in µM.
    
    Returns:
        Eine Liste von Dictionaries, jedes mit den Schlüsseln
        'time_ms', 'temp_c', 'ph', 'fluorescence_au'.
    """
    if duration_s <= 0:
        return []
    
    interval_s = interval_ms / 1000.0
    if interval_s <= 0:
        interval_s = 0.1  # Fallback, um Division durch 0 zu vermeiden
    
    num_points = int(duration_s / interval_s) + 1
    series = []
    
    for i in range(num_points):
        t_s = i * interval_s
        temp_c = simulate_temperature(t_s, target_temp_c)
        ph = simulate_ph(t_s, ph_start, delta_ph, k_ph)
        fluor = simulate_fluorescence(ph, pka, fluor_conc_um)
        
        series.append({
            "time_ms": int(t_s * 1000),
            "temp_c": round(temp_c, 3),
            "ph": round(ph, 3),
            "fluorescence_au": round(fluor, 3),
        })
    
    return series

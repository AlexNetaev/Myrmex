"""
src/castes/hardware_profile.py
Lädt und validiert Hardware-Profile aus hardware_profiles/.

Ein Hardware-Profil beschreibt, wie eine spezifische Hardware zu bedienen
ist. Wenn die Hardware wechselt, wird nur das Profil ausgetauscht — nicht
der Code.
"""
from __future__ import annotations
import logging
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger("caste.hardware_profile")

# ---------------------------------------------------------------------------
# Pydantic-Modelle für das Hardware-Profil
# ---------------------------------------------------------------------------

class ParameterLimit(BaseModel):
    """Min/Max für einen einzelnen Parameter."""
    model_config = ConfigDict(extra="forbid")
    min: float | None = None
    max: float | None = None

class ReagentSpec(BaseModel):
    """Spezifikation eines einzelnen Reagenz."""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    role: str = Field(default="")
    concentration_range_mm: list[float] = Field(default_factory=list)
    volume_range_ul: list[float] = Field(default_factory=list)

class ReagentsConfig(BaseModel):
    """Reagenzien-Konfiguration."""
    model_config = ConfigDict(extra="forbid")
    expected: list[ReagentSpec] = Field(default_factory=list)
    total_volume_max_ul: float | None = None

class ConversionConfig(BaseModel):
    """Umrechnungs-Konfiguration."""
    model_config = ConfigDict(extra="allow")  # Flexibel für verschiedene Formeln
    formula: str = Field(default="linear")
    description: str = Field(default="")
    parameters: dict = Field(default_factory=dict)

class ExperimentSchemaConfig(BaseModel):
    """Experiment-Schema-Konfiguration."""
    model_config = ConfigDict(extra="allow")
    required_fields: list[str] = Field(default_factory=list)
    parameters_schema: dict = Field(default_factory=dict)
    reagents_format: str = Field(default="list")

class OutputFileSpec(BaseModel):
    """Spezifikation einer Output-Datei."""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    description: str = Field(default="")
    columns: list[str] = Field(default_factory=list)

class HardwareProfile(BaseModel):
    """Das vollständige Hardware-Profil."""
    model_config = ConfigDict(extra="forbid")
    
    metadata: dict = Field(default_factory=dict)
    limits: dict[str, ParameterLimit] = Field(default_factory=dict)
    reagents: ReagentsConfig = Field(default_factory=ReagentsConfig)
    conversions: dict[str, ConversionConfig] = Field(default_factory=dict)
    experiment_schema: ExperimentSchemaConfig = Field(default_factory=ExperimentSchemaConfig)
    output_files: list[OutputFileSpec] = Field(default_factory=list)
    defaults: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Loader-Funktion
# ---------------------------------------------------------------------------

def load_hardware_profile(profile_path: Path) -> HardwareProfile:
    """
    Lädt ein Hardware-Profil aus einer YAML-Datei.
    
    Args:
        profile_path: Pfad zur YAML-Datei.
    
    Returns:
        Das validierte HardwareProfile.
    
    Raises:
        FileNotFoundError: Wenn die Datei nicht existiert.
        yaml.YAMLError: Wenn die Datei kein gültiges YAML ist.
        Exception: Wenn die Validierung fehlschlägt.
    """
    if not profile_path.exists():
        raise FileNotFoundError(f"Hardware-Profil nicht gefunden: {profile_path}")
    
    raw_text = profile_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)
    
    if not isinstance(raw_data, dict):
        raise ValueError(f"Hardware-Profil muss ein YAML-Mapping sein: {profile_path}")
    
    return HardwareProfile.model_validate(raw_data)


def find_active_profile(profiles_dir: Path, experiment_type: str | None = None) -> Path | None:
    """
    Findet das aktive Hardware-Profil im profiles_dir.
    
    Wenn experiment_type angegeben ist, wird nach einem Profil mit
    passendem metadata.experiment_type gesucht. Sonst wird das erste
    Profil zurückgegeben.
    
    Args:
        profiles_dir: Verzeichnis mit den Hardware-Profilen.
        experiment_type: Optionaler Experiment-Typ zur Filterung.
    
    Returns:
        Pfad zum aktiven Profil, oder None wenn keines gefunden wurde.
    """
    if not profiles_dir.exists():
        return None
    
    yaml_files = sorted(profiles_dir.glob("*.yaml"))
    if not yaml_files:
        return None
    
    if experiment_type is None:
        return yaml_files[0]
    
    for yaml_file in yaml_files:
        try:
            profile = load_hardware_profile(yaml_file)
            if profile.metadata.get("experiment_type") == experiment_type:
                return yaml_file
        except Exception as e:
            logger.warning(f"Konnte Profil {yaml_file} nicht laden: {e}")
            continue
    
    return None

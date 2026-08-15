"""
src/workspace/workspace_manager.py
Verwaltet die Workspace-Struktur von Myrmex.
"""
from __future__ import annotations
import logging
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """
    Legt die Workspace-Struktur idempotent an.
    
    WICHTIG: Überschreibt NIEMALS eine existierende Datei.
    Legt nur fehlende Verzeichnisse/Dateien an.
    """
    
    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root: Path = (workspace_root or config.WORKSPACE_ROOT).resolve()
        
        # Verzeichnisse
        self.system_dir = self.workspace_root / "00_System"
        self.pheromon_field_dir = self.workspace_root / "01_Pheromon_Field"
        self.trails_dir = self.pheromon_field_dir / "trails"
        self.crystals_dir = self.pheromon_field_dir / "crystals"
        self.warnings_dir = self.pheromon_field_dir / "warnings"
        self.research_cycles_dir = self.workspace_root / "02_Research_Cycles"
        self.hardware_queue_dir = self.workspace_root / "03_Hardware_Queue"
        self.processed_queue_dir = self.hardware_queue_dir / "_processed"
        self.failed_queue_dir = self.hardware_queue_dir / "_failed"
        self.knowledge_base_dir = self.workspace_root / "04_Knowledge_Base"
        self.knowledge_base_archive_dir = self.knowledge_base_dir / "Archive"
        self.loops_dir = self.workspace_root / "05_Loops"
    
    def initialize(self) -> None:
        """Legt die Workspace-Struktur idempotent an."""
        logger.info("Initializing Myrmex workspace at: %s", self.workspace_root)
        self._create_directories()
        self._create_placeholder_files()
        logger.info("Workspace initialization complete.")
    
    def is_initialized(self) -> bool:
        """Prüft, ob der Workspace vollständig initialisiert ist."""
        required_dirs = [
            self.workspace_root, self.system_dir, self.pheromon_field_dir,
            self.trails_dir, self.crystals_dir, self.warnings_dir,
            self.research_cycles_dir, self.hardware_queue_dir,
            self.processed_queue_dir, self.failed_queue_dir,
            self.knowledge_base_dir, self.knowledge_base_archive_dir,
            self.loops_dir,
        ]
        return all(d.is_dir() for d in required_dirs)
    
    def _create_directories(self) -> None:
        """Legt alle Verzeichnisse an (idempotent)."""
        directories = [
            self.workspace_root, self.system_dir, self.pheromon_field_dir,
            self.trails_dir, self.crystals_dir, self.warnings_dir,
            self.research_cycles_dir, self.hardware_queue_dir,
            self.processed_queue_dir, self.failed_queue_dir,
            self.knowledge_base_dir, self.knowledge_base_archive_dir,
            self.loops_dir,
            # NEU: Hardware-Profiles-Verzeichnis
            self.workspace_root / "hardware_profiles",
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)
    
    def _create_placeholder_files(self) -> None:
        """Legt Platzhalter-Dateien an (nur wenn sie nicht existieren)."""
        # directive.md (leer)
        directive = self.system_dir / "directive.md"
        if not directive.exists():
            directive.write_text("# Myrmex Directive\n\n*(No directive set yet.)*\n", encoding="utf-8")
        
        # theory_baseline.md (leer)
        theory = self.knowledge_base_dir / "theory_baseline.md"
        if not theory.exists():
            theory.write_text("# Myrmex Theory Baseline\n\n*(No findings recorded yet.)*\n", encoding="utf-8")
        
        # NEU: Hardware-Profil erstellen (falls nicht vorhanden)
        self._create_hardware_profile()

    def _create_hardware_profile(self) -> None:
        """Erstellt das Hardware-Profil für den Dummy, falls nicht vorhanden."""
        hardware_profile_path = self.workspace_root / "hardware_profiles" / "orbus_dummy_v2.yaml"
        
        if hardware_profile_path.exists():
            return  # Bereits vorhanden
        
        # Hardware-Profil aus dem Projekt-Root kopieren (myrmex/hardware_profiles/)
        project_root = Path(__file__).resolve().parent.parent.parent
        source_profile_path = project_root / "hardware_profiles" / "orbus_dummy_v2.yaml"
        
        if source_profile_path.exists():
            import shutil
            shutil.copy2(source_profile_path, hardware_profile_path)
            logger.info(f"Copied hardware profile to {hardware_profile_path}")
        else:
            logger.warning(
                f"Hardware profile not found at {source_profile_path}. "
                f"Creating minimal profile."
            )
            # Minimales Profil erstellen
            hardware_profile_path.write_text(
                "# Minimal Hardware Profile\n"
                "metadata:\n"
                "  name: 'Minimal Profile'\n"
                "  version: '1.0.0'\n",
                encoding="utf-8",
            )

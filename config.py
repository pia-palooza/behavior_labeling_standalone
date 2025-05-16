# === START FILE: scripts/behavior_annotator/config.py ===
# config.py
"""
Configuration constants for the Behavior Annotator application.
"""
import sys
from typing import List

# --- Basic Configuration ---
# Default fallback frame rate if video doesn't report one
DEFAULT_FALLBACK_FPS: float = 30.0
# Default playback speed
DEFAULT_PLAYBACK_SPEED: float = 1.0
# Default list of behavior identities (can be customized or loaded from file)
DEFAULT_BEHAVIOR_IDENTITIES: List[str] = [ "nose_to_nose", "attack", "rearing", "grooming_self", "grooming_intruder", "mounting", "mouse_added" ]

# --- Table Column Indices ---
COL_BEHAVIOR: int = 0
COL_START_FRAME: int = 1
COL_END_FRAME: int = 2
COL_DURATION: int = 3

# --- Playback States ---
STATE_STOPPED: int = 0
STATE_PLAYING: int = 1
STATE_PAUSED: int = 2

# --- Unsaved Changes Dialog Results ---
PROCEED_SAVE: int = 1
PROCEED_DISCARD: int = 2
PROCEED_CANCEL: int = 0

PROJECT_DIR: str = r"D:\SIMBA\Mea_bilatstim_RI-PJA-PJA-2025-03-30\project_folder"

# === END FILE: scripts/behavior_annotator/config.py ===
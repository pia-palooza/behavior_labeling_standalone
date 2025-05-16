# === START FILE: scripts/behavior_annotator/utils.py ===
# utils.py
"""
Utility functions for the Behavior Annotator application.
"""
import logging
import math

import numpy as np
import pandas as pd

def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.ms format."""
    if seconds < 0: seconds = 0
    # Handle potential NaN values gracefully
    if pd.isna(seconds) or not np.isfinite(seconds): return "--:--:--.---"
    try:
        # Ensure seconds is a standard Python float for divmod
        seconds = float(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        # Calculate milliseconds from the fractional part of the original seconds
        ms = int(round((seconds - math.floor(seconds)) * 1000))
        # Ensure integer parts are used for formatting
        return f"{int(h):02d}:{int(m):02d}:{int(math.floor(s)):02d}.{ms:03d}"
    except (TypeError, ValueError) as e:
        logging.error(f"Error formatting timestamp for value {seconds}: {e}")
        return "--:--:--.---"

# === END FILE: scripts/behavior_annotator/utils.py ===
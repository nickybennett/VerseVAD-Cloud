"""Streamlit Community Cloud entrypoint for the private VerseVAD deployment."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# The ordinary Windows and macOS launchers execute the source application
# directly, so this private cloud-safety mode does not affect local installs.
# Restore any pre-existing process value after the rerun so test harnesses and
# embedded callers cannot accidentally inherit cloud-only storage semantics.
_previous_cloud_mode = os.environ.get("VERSEVAD_CLOUD_DEPLOYMENT")
os.environ["VERSEVAD_CLOUD_DEPLOYMENT"] = "1"
try:
    # Streamlit re-executes this entrypoint for every widget interaction.
    # Importing the UI module directly can become a no-op once Python has cached
    # the module, leaving a blank page on a later rerun. Execute the source
    # application afresh so hosted reruns follow the local launcher lifecycle.
    runpy.run_path(
        str(SOURCE_ROOT / "versevad" / "ui" / "app.py"),
        run_name="__main__",
    )
finally:
    if _previous_cloud_mode is None:
        os.environ.pop("VERSEVAD_CLOUD_DEPLOYMENT", None)
    else:
        os.environ["VERSEVAD_CLOUD_DEPLOYMENT"] = _previous_cloud_mode

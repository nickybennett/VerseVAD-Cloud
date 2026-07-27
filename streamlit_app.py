"""Streamlit Community Cloud entrypoint for the private VerseVAD deployment."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# The ordinary Windows and macOS launchers execute the source application
# directly, so this private cloud-safety mode does not affect local installs.
os.environ["VERSEVAD_CLOUD_DEPLOYMENT"] = "1"

from versevad.ui import app as _versevad_app  # noqa: E402,F401

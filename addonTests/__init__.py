# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Unit tests for the add-on.

These tests run inside NVDA's own unit test environment, using a built NVDA source checkout
(liblouis and NVDA's Python dependencies are required).
Set the ``NVDA_REPO`` environment variable to the NVDA source checkout,
it defaults to an ``nvda`` directory next to this repository.
Run them with the Python interpreter of NVDA's virtual environment from the add-on directory, e.g.:

	..\\nvda\\.venv\\Scripts\\python.exe -m unittest discover -s addonTests -t .
"""

import os
import sys

_ADDON_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NVDA_REPO = os.path.abspath(os.environ.get("NVDA_REPO", os.path.join(_ADDON_REPO, "..", "nvda")))

sys.path.insert(0, NVDA_REPO)
# Importing NVDA's unit test package initializes NVDA's configuration, braille handler, etc.
import tests.unit  # noqa: E402, F401
import addonHandler  # noqa: E402

# Add-on translations can only be initialized for installed add-ons.
addonHandler.initTranslation = lambda: None

sys.path.insert(0, os.path.join(_ADDON_REPO, "addon", "globalPlugins"))

# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""CJK Braille Enhancements.

Implements braille features requested for continuous script languages such as Chinese:

* Text wrap for continuous CJK text, https://github.com/nvaccess/nvda/issues/18295
* Spacing between Chinese characters, Latin letters and numbers, https://github.com/nvaccess/nvda/issues/20726
"""

from typing import override

import addonHandler
import braille
import globalPluginHandler
import inputCore
import ui
from globalCommands import SCRCAT_BRAILLE
from gui.settingsDialogs import NVDASettingsDialog
from logHandler import log
from scriptHandler import script

from . import addonConfig, spacing, textWrap
from .addonConfig import CJKTextWrap
from .settingsPanel import CJKBrailleSettingsPanel

addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		addonConfig.register()
		NVDASettingsDialog.categoryClasses.append(CJKBrailleSettingsPanel)
		self._textWrapInstalled = textWrap.install()
		spacing.install()
		log.debug("CJK Braille Enhancements initialized")

	@override
	def terminate(self):
		spacing.uninstall()
		textWrap.uninstall()
		try:
			NVDASettingsDialog.categoryClasses.remove(CJKBrailleSettingsPanel)
		except ValueError:
			pass
		super().terminate()

	@script(
		# Translators: Input help mode message for the command to cycle through CJK text wrap modes.
		description=_("Cycle through the braille text wrap modes for CJK characters"),
		category=SCRCAT_BRAILLE,
	)
	def script_cycleCJKTextWrap(self, gesture: inputCore.InputGesture) -> None:
		if not self._textWrapInstalled:
			# Translators: Reported when CJK text wrap can't be used with this version of NVDA.
			ui.message(_("CJK text wrap is unavailable"))
			return
		modes = list(CJKTextWrap)
		newMode = modes[(modes.index(addonConfig.getTextWrap()) + 1) % len(modes)]
		addonConfig.setTextWrap(newMode)
		braille.handler.initialDisplay()
		# Translators: Reports the CJK text wrap mode, e.g. "CJK text wrap At character boundaries".
		ui.message(_("CJK text wrap {mode}").format(mode=newMode.displayString))

	@script(
		description=_(
			# Translators: Input help mode message for the command to toggle spacing in Chinese braille.
			"Toggles inserting spaces between Chinese characters, Latin letters and numbers in braille",
		),
		category=SCRCAT_BRAILLE,
	)
	def script_toggleCJKSpacing(self, gesture: inputCore.InputGesture) -> None:
		enabled = not addonConfig.isSpacingEnabled()
		addonConfig.setSpacingEnabled(enabled)
		braille.handler.initialDisplay()
		if enabled:
			# Translators: Reported when inserting spaces between Chinese characters, Latin letters and numbers is turned on.
			ui.message(_("Chinese braille spacing on"))
		else:
			# Translators: Reported when inserting spaces between Chinese characters, Latin letters and numbers is turned off.
			ui.message(_("Chinese braille spacing off"))

# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Settings panel of the add-on, shown in NVDA's settings dialog."""

from typing import override

import addonHandler
import wx
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import SettingsPanel

from . import addonConfig
from .addonConfig import CJKTextWrap, SpacingBoundary

addonHandler.initTranslation()


class CJKBrailleSettingsPanel(SettingsPanel):
	# Translators: The title of the settings panel of the CJK Braille Enhancements add-on.
	title = _("CJK Braille")

	@override
	def makeSettings(self, sizer: wx.BoxSizer) -> None:
		sHelper = guiHelper.BoxSizerHelper(self, sizer=sizer)

		self.textWrapList: wx.Choice = sHelper.addLabeledControl(
			# Translators: The label for a setting in the CJK Braille settings panel
			# to choose how continuous CJK text (e.g. Chinese) wraps on the braille display.
			_("&Text wrap for CJK characters:"),
			wx.Choice,
			choices=[mode.displayString for mode in CJKTextWrap],
		)
		self.textWrapList.SetSelection(list(CJKTextWrap).index(addonConfig.getTextWrap()))

		self.insertSpacesCheckBox: wx.CheckBox = sHelper.addItem(
			wx.CheckBox(
				self,
				# Translators: The label for a checkbox in the CJK Braille settings panel.
				label=_("&Insert spaces between Chinese characters, Latin letters and numbers"),
			),
		)
		self.insertSpacesCheckBox.SetValue(addonConfig.isSpacingEnabled())
		self.insertSpacesCheckBox.Bind(wx.EVT_CHECKBOX, self._onInsertSpacesChange)

		self._boundaries = list(SpacingBoundary)
		self.boundariesList: nvdaControls.CustomCheckListBox = sHelper.addLabeledControl(
			# Translators: The label for a list of checkboxes in the CJK Braille settings panel
			# to choose where spaces are inserted.
			_("Insert spaces &at:"),
			nvdaControls.CustomCheckListBox,
			choices=[boundary.displayString for boundary in self._boundaries],
		)
		self.boundariesList.CheckedItems = [
			index
			for index, boundary in enumerate(self._boundaries)
			if addonConfig.isSpacingBoundaryEnabled(boundary)
		]
		self.boundariesList.SetSelection(0)
		self.boundariesList.Enable(self.insertSpacesCheckBox.IsChecked())

	def _onInsertSpacesChange(self, evt: wx.CommandEvent) -> None:
		self.boundariesList.Enable(evt.IsChecked())

	@override
	def onSave(self) -> None:
		addonConfig.setTextWrap(list(CJKTextWrap)[self.textWrapList.GetSelection()])
		addonConfig.setSpacingEnabled(self.insertSpacesCheckBox.IsChecked())
		checkedItems = set(self.boundariesList.CheckedItems)
		for index, boundary in enumerate(self._boundaries):
			addonConfig.setSpacingBoundary(boundary, index in checkedItems)

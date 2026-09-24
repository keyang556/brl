# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Tests for the global plugin, its scripts and its settings panel."""

import unittest
from unittest.mock import patch

import louisHelper
import wx
from braille.buffers import BrailleBuffer
from cjkBrailleEnhancements import GlobalPlugin, addonConfig, spacing, textWrap
from cjkBrailleEnhancements.addonConfig import CJKTextWrap, SpacingBoundary
from cjkBrailleEnhancements.settingsPanel import CJKBrailleSettingsPanel
from gui.settingsDialogs import NVDASettingsDialog


class TestGlobalPlugin(unittest.TestCase):
	def setUp(self):
		self.plugin = GlobalPlugin()

	def tearDown(self):
		self.plugin.terminate()
		addonConfig.setTextWrap(CJKTextWrap.FOLLOW_NVDA)
		addonConfig.setSpacingEnabled(False)

	def test_lifecycle(self):
		self.assertIn(CJKBrailleSettingsPanel, NVDASettingsDialog.categoryClasses)
		self.assertIs(louisHelper.translate, spacing._translate)
		self.assertIs(BrailleBuffer._nextWindow, textWrap._nextWindow)
		self.plugin.terminate()
		self.assertNotIn(CJKBrailleSettingsPanel, NVDASettingsDialog.categoryClasses)
		self.assertIsNot(louisHelper.translate, spacing._translate)
		self.assertIsNot(BrailleBuffer._nextWindow, textWrap._nextWindow)
		self.plugin = GlobalPlugin()

	@patch("ui.message")
	def test_cycleTextWrap(self, message):
		modes = list(CJKTextWrap)
		for expected in modes[1:] + modes[:1]:
			self.plugin.script_cycleCJKTextWrap(None)
			self.assertEqual(addonConfig.getTextWrap(), expected)
			message.assert_called_with(f"CJK text wrap {expected.displayString}")

	@patch("ui.message")
	def test_toggleSpacing(self, message):
		self.plugin.script_toggleCJKSpacing(None)
		self.assertTrue(addonConfig.isSpacingEnabled())
		message.assert_called_with("Chinese braille spacing on")
		self.plugin.script_toggleCJKSpacing(None)
		self.assertFalse(addonConfig.isSpacingEnabled())
		message.assert_called_with("Chinese braille spacing off")

	def test_scriptsHaveNoDefaultGestures(self):
		self.assertFalse(getattr(GlobalPlugin, "_GlobalPlugin__gestures", {}))


class TestSettingsPanel(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = wx.App()

	def setUp(self):
		addonConfig.register()
		self.frame = wx.Frame(None)

	def tearDown(self):
		self.frame.Destroy()
		addonConfig.setTextWrap(CJKTextWrap.FOLLOW_NVDA)
		addonConfig.setSpacingEnabled(False)
		for boundary in SpacingBoundary:
			addonConfig.setSpacingBoundary(boundary, boundary is not SpacingBoundary.LATIN_NUMBER)

	def test_loadAndSave(self):
		addonConfig.setTextWrap(CJKTextWrap.OVERLAP)
		panel = CJKBrailleSettingsPanel(self.frame)
		self.assertEqual(panel.textWrapList.GetSelection(), list(CJKTextWrap).index(CJKTextWrap.OVERLAP))
		self.assertFalse(panel.insertSpacesCheckBox.IsChecked())
		self.assertFalse(panel.boundariesList.IsEnabled())
		self.assertEqual(list(panel.boundariesList.CheckedItems), [0, 1])
		panel.textWrapList.SetSelection(list(CJKTextWrap).index(CJKTextWrap.CHARACTER_BOUNDARIES))
		panel.insertSpacesCheckBox.SetValue(True)
		panel.boundariesList.CheckedItems = [1, 2]
		panel.onSave()
		self.assertEqual(addonConfig.getTextWrap(), CJKTextWrap.CHARACTER_BOUNDARIES)
		self.assertEqual(
			addonConfig.getSpacingBoundaries(),
			frozenset((SpacingBoundary.CHINESE_NUMBER, SpacingBoundary.LATIN_NUMBER)),
		)

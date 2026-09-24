# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Tests for spacing between Chinese characters, Latin letters and numbers (NVDA issue 20726)."""

import unittest

import braille
import brailleTables
import config
import louisHelper
from braille.regions.base import TextRegion
from cjkBrailleEnhancements import addonConfig, spacing
from cjkBrailleEnhancements.addonConfig import SpacingBoundary
from cjkBrailleEnhancements.spacing import BoundarySpacingOffsetConverter, getBoundaryTypes

_DEFAULT_BOUNDARIES = getBoundaryTypes((SpacingBoundary.CHINESE_LATIN, SpacingBoundary.CHINESE_NUMBER))
_ALL_BOUNDARIES = getBoundaryTypes(SpacingBoundary)


def _space(text: str, boundaries=_DEFAULT_BOUNDARIES) -> str:
	return BoundarySpacingOffsetConverter(text, boundaries).encoded


class TestConverter(unittest.TestCase):
	def test_examplesFromIssue(self):
		self.assertEqual(_space("使用NVDA閱讀"), "使用 NVDA 閱讀")
		self.assertEqual(_space("版本2026.3已發布"), "版本 2026.3 已發布")

	def test_consecutiveChineseUnchanged(self):
		"""No word segmentation is performed."""
		self.assertEqual(_space("這是一個測試"), "這是一個測試")

	def test_existingSpacesNotDoubled(self):
		self.assertEqual(_space("使用 NVDA 閱讀"), "使用 NVDA 閱讀")

	def test_punctuationNotSpaced(self):
		self.assertEqual(_space("NVDA，你好"), "NVDA，你好")
		self.assertEqual(_space("「NVDA」"), "「NVDA」")

	def test_latinAndNumbers(self):
		self.assertEqual(_space("NVDA2026版"), "NVDA2026 版")
		self.assertEqual(_space("NVDA2026版", _ALL_BOUNDARIES), "NVDA 2026 版")

	def test_singleBoundaryType(self):
		self.assertEqual(
			_space("第3章Python", getBoundaryTypes((SpacingBoundary.CHINESE_NUMBER,))),
			"第 3 章Python",
		)

	def test_bopomofoAndAccentedLatin(self):
		self.assertEqual(_space("ㄅㄆㄇabc"), "ㄅㄆㄇ abc")
		self.assertEqual(_space("咖啡café好"), "咖啡 café 好")

	def test_offsets(self):
		text = "使用NVDA閱讀"
		converter = BoundarySpacingOffsetConverter(text, _DEFAULT_BOUNDARIES)
		self.assertEqual(converter.encoded, "使用 NVDA 閱讀")
		self.assertEqual(converter.insertedCount, 2)
		self.assertEqual(
			[converter.strToEncodedOffsets(i) for i in range(len(text))],
			[0, 1, 3, 4, 5, 6, 8, 9],
		)
		# Separators map to the character that follows them.
		self.assertEqual(
			[converter.encodedToStrOffsets(i) for i in range(converter.encodedStringLength)],
			[0, 1, 2, 2, 3, 4, 5, 6, 6, 7],
		)
		self.assertEqual(converter.strToEncodedOffsets(len(text)), converter.encodedStringLength)
		self.assertEqual(converter.encodedToStrOffsets(converter.encodedStringLength), len(text))
		self.assertEqual(converter.strToEncodedOffsets(2, 6), (3, 8))
		self.assertEqual(converter.encodedToStrOffsets(2, 9), (2, 7))


class _SpacingEnabledTestCase(unittest.TestCase):
	def setUp(self):
		addonConfig.register()
		self._oldTable = braille.handler.table
		braille.handler.table = brailleTables.getTable("zh-tw.ctb")
		addonConfig.setSpacingEnabled(True)
		for boundary in SpacingBoundary:
			addonConfig.setSpacingBoundary(boundary, boundary is not SpacingBoundary.LATIN_NUMBER)
		spacing.install()

	def tearDown(self):
		spacing.uninstall()
		addonConfig.setSpacingEnabled(False)
		braille.handler.table = self._oldTable


class TestTranslate(_SpacingEnabledTestCase):
	def test_translate(self):
		text = "使用NVDA閱讀"
		tables = ["zh-tw.ctb", "braille-patterns.cti"]
		cells, brailleToRawPos, rawToBraillePos, cursorPos = louisHelper.translate(tables, text, cursorPos=2)
		spaced = spacing._originalTranslate(tables, "使用 NVDA 閱讀", cursorPos=3)
		self.assertEqual(cells, spaced[0])
		self.assertEqual(cursorPos, spaced[3])
		self.assertEqual(len(brailleToRawPos), len(cells))
		self.assertEqual(len(rawToBraillePos), len(text))
		self.assertTrue(all(0 <= pos < len(text) for pos in brailleToRawPos))
		# The inserted spaces are blank cells right before N and 閱.
		self.assertEqual(cells[rawToBraillePos[2] - 1], 0)
		self.assertEqual(cells[rawToBraillePos[6] - 1], 0)
		self.assertEqual(brailleToRawPos[rawToBraillePos[2] - 1], 2)

	def test_typeforms(self):
		text = "使用NVDA"
		typeform = [louisHelper.Typeform.PLAIN_TEXT] * 2 + [louisHelper.Typeform.BOLD] * 4
		cells = louisHelper.translate(["zh-tw.ctb"], text, typeform=typeform)[0]
		# The inserted space takes the typeform of the character that follows it.
		spacedTypeform = typeform[:2] + [louisHelper.Typeform.BOLD] + typeform[2:]
		self.assertEqual(
			cells,
			spacing._originalTranslate(["zh-tw.ctb"], "使用 NVDA", typeform=spacedTypeform)[0],
		)

	def test_disabled(self):
		addonConfig.setSpacingEnabled(False)
		text = "使用NVDA閱讀"
		self.assertEqual(
			louisHelper.translate(["zh-tw.ctb"], text),
			spacing._originalTranslate(["zh-tw.ctb"], text),
		)

	def test_nonChineseTable(self):
		text = "使用NVDA閱讀"
		self.assertEqual(
			louisHelper.translate(["en-ueb-g1.ctb"], text),
			spacing._originalTranslate(["en-ueb-g1.ctb"], text),
		)

	def test_isChineseTable(self):
		self.assertTrue(spacing.isChineseTable("zh-tw.ctb"))
		self.assertTrue(spacing.isChineseTable("zh-hk.ctb"))
		self.assertTrue(spacing.isChineseTable("zhcn-g2.ctb"))
		self.assertFalse(spacing.isChineseTable("en-ueb-g2.ctb"))

	def test_uninstallRestores(self):
		spacing.uninstall()
		self.assertIsNot(louisHelper.translate, spacing._translate)
		spacing.install()
		self.assertIs(louisHelper.translate, spacing._translate)


class TestRegion(_SpacingEnabledTestCase):
	def test_regionUpdate(self):
		region = TextRegion("版本2026.3已發布")
		region.cursorPos = 6
		region.update()
		self.assertEqual(len(region.rawToBraillePos), len(region.rawText))
		self.assertEqual(len(region.brailleToRawPos), len(region.brailleCells))
		# Spaces before 2 and 已.
		self.assertEqual(region.brailleCells[region.rawToBraillePos[2] - 1], 0)
		self.assertEqual(region.brailleCells[region.rawToBraillePos[8] - 1], 0)
		self.assertEqual(region.brailleCursorPos, region.rawToBraillePos[6])

	def test_regionWithChineseWordSegmentation(self):
		"""Spacing does not add a second space where word segmentation already inserted one."""
		braille.handler.table = brailleTables.getTable("zh-chn.ctb")
		self.assertTrue(config.conf["braille"]["useChineseWordSegmentation"])
		region = TextRegion("使用NVDA阅读")
		region.update()
		self.assertEqual(len(region.rawToBraillePos), len(region.rawText))
		cells = region.brailleCells
		self.assertFalse(any(cells[i] == 0 and cells[i + 1] == 0 for i in range(len(cells) - 1)))

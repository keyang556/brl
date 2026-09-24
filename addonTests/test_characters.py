# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Tests for character classification."""

import unittest

from cjkBrailleEnhancements.characters import CharacterType, getCharacterType, isChinese, isContinuousScript


class TestCharacters(unittest.TestCase):
	def test_continuousScript(self):
		for char in "中文ㄅㄆあアー，。、「」【】〇々ＡＢ１":
			self.assertTrue(isContinuousScript(char), msg=char)
		for char in "Aa1 ,.éΩ한":
			self.assertFalse(isContinuousScript(char), msg=char)

	def test_overlappingRanges(self):
		"""Characters in CJK Symbols and Punctuation after the Han ranges inside that block are CJK."""
		for codePoint in range(0x3000, 0x3040):
			self.assertTrue(isContinuousScript(chr(codePoint)), msg=hex(codePoint))

	def test_chinese(self):
		for char in "中文〇ㄅ𠀀":
			self.assertTrue(isChinese(char), msg=char)
		for char in "あ，【A1":
			self.assertFalse(isChinese(char), msg=char)

	def test_characterType(self):
		self.assertEqual(getCharacterType("中"), CharacterType.CHINESE)
		self.assertEqual(getCharacterType("N"), CharacterType.LATIN)
		self.assertEqual(getCharacterType("é"), CharacterType.LATIN)
		self.assertEqual(getCharacterType("7"), CharacterType.NUMBER)
		self.assertEqual(getCharacterType("，"), CharacterType.OTHER)
		self.assertEqual(getCharacterType("Ω"), CharacterType.OTHER)

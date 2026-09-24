# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Classification of characters used by the text wrap and spacing features."""

import bisect
import enum
import unicodedata
from collections.abc import Sequence

_HAN_RANGES: tuple[tuple[int, int], ...] = (
	(0x2E80, 0x2EFF),  # CJK Radicals Supplement
	(0x2F00, 0x2FDF),  # Kangxi Radicals
	(0x3005, 0x3005),  # Ideographic iteration mark
	(0x3007, 0x3007),  # Ideographic number zero
	(0x3021, 0x3029),  # Hangzhou numerals
	(0x3038, 0x303B),  # Hangzhou numerals and vertical ideographic iteration mark
	(0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
	(0x4E00, 0x9FFF),  # CJK Unified Ideographs
	(0xF900, 0xFAFF),  # CJK Compatibility Ideographs
	(0x20000, 0x323AF),  # CJK Unified Ideographs Extensions B to H, CJK Compatibility Ideographs Supplement
)
"""Code point ranges (inclusive) of Han ideographs."""

_BOPOMOFO_RANGES: tuple[tuple[int, int], ...] = (
	(0x3100, 0x312F),  # Bopomofo
	(0x31A0, 0x31BF),  # Bopomofo Extended
)
"""Code point ranges (inclusive) of Bopomofo (Zhuyin) characters."""

_OTHER_CJK_RANGES: tuple[tuple[int, int], ...] = (
	(0x3000, 0x303F),  # CJK Symbols and Punctuation
	(0x3040, 0x30FF),  # Hiragana and Katakana
	(0x31F0, 0x31FF),  # Katakana Phonetic Extensions
	(0x3200, 0x33FF),  # Enclosed CJK Letters and Months, CJK Compatibility
	(0xFE10, 0xFE1F),  # Vertical Forms
	(0xFE30, 0xFE4F),  # CJK Compatibility Forms
	(0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
)
"""Code point ranges (inclusive) of other characters used in continuous CJK text."""


def _buildLookup(*rangeGroups: Sequence[tuple[int, int]]) -> tuple[list[int], list[int]]:
	ranges = sorted(r for group in rangeGroups for r in group)
	return [start for start, _end in ranges], [end for _start, end in ranges]


def _inRanges(char: str, lookup: tuple[list[int], list[int]]) -> bool:
	if len(char) != 1:
		return False
	starts, ends = lookup
	codePoint = ord(char)
	index = bisect.bisect_right(starts, codePoint) - 1
	return index >= 0 and codePoint <= ends[index]


_CHINESE_LOOKUP = _buildLookup(_HAN_RANGES, _BOPOMOFO_RANGES)
_CJK_LOOKUP = _buildLookup(_HAN_RANGES, _BOPOMOFO_RANGES, _OTHER_CJK_RANGES)


def isChinese(char: str) -> bool:
	"""Whether the given character is a Chinese character (a Han ideograph or Bopomofo)."""
	return _inRanges(char, _CHINESE_LOOKUP)


def isContinuousScript(char: str) -> bool:
	"""Whether the given character belongs to continuous CJK text,
	i.e. text in which every character boundary is an acceptable line break opportunity.
	This covers Han ideographs, Bopomofo, Kana, CJK punctuation and full width forms.
	"""
	return _inRanges(char, _CJK_LOOKUP)


class CharacterType(enum.Enum):
	"""Character types between which spaces can be inserted."""

	OTHER = enum.auto()
	CHINESE = enum.auto()
	LATIN = enum.auto()
	NUMBER = enum.auto()


def getCharacterType(char: str) -> CharacterType:
	"""Get the :class:`CharacterType` of a character."""
	if isChinese(char):
		return CharacterType.CHINESE
	if "0" <= char <= "9":
		return CharacterType.NUMBER
	if char.isalpha() and (char.isascii() or unicodedata.name(char, "").startswith("LATIN ")):
		return CharacterType.LATIN
	return CharacterType.OTHER

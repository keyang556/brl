# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Optional spacing between Chinese characters, Latin letters and numbers in Chinese braille output.

See https://github.com/nvaccess/nvda/issues/20726.
Consecutive Chinese characters are left unchanged, i.e. no word segmentation is performed.
A space is only inserted where the character type changes and there is no space already.
The spaces are inserted before liblouis translation, like NVDA's Chinese word segmentation,
and all offsets returned to NVDA remain relative to the original text.
"""

from collections.abc import Callable, Collection, Sequence
from functools import cache
from typing import cast, override

import louisHelper
from logHandler import log
from textUtils import OffsetConverter

from . import addonConfig
from .characters import CharacterType, getCharacterType

_CHINESE_LANGUAGES: frozenset[str] = frozenset(
	(
		"zh",
		"cmn",  # Mandarin, used by zh-tw.ctb
		"yue",  # Cantonese
		"nan",  # Min Nan
		"hak",  # Hakka
		"wuu",  # Wu
		"gan",
		"hsn",
		"cdo",
		"cjy",
		"cpx",
		"czh",
		"czo",
		"mnp",
		"lzh",
	),
)
"""Primary language subtags of Chinese languages."""


class BoundarySpacingOffsetConverter(OffsetConverter):
	"""An offset converter for text with spaces inserted at character type boundaries.

	Inserted separators map to the position of the character that follows them,
	like the separators inserted by NVDA's Chinese word segmentation.
	"""

	sep: str = " "

	def __init__(self, text: str, boundaries: Collection[frozenset[CharacterType]]) -> None:
		"""
		:param text: The text to insert spaces in.
		:param boundaries: Pairs of character types between which a space should be inserted.
		"""
		super().__init__(text)
		encodedChars: list[str] = []
		strToEncoded: list[int] = []
		encodedToStr: list[int] = []
		previousType: CharacterType | None = None
		for strIndex, char in enumerate(text):
			charType = getCharacterType(char)
			if previousType is not None and frozenset((previousType, charType)) in boundaries:
				encodedToStr.append(strIndex)
				encodedChars.append(self.sep)
			strToEncoded.append(len(encodedChars))
			encodedToStr.append(strIndex)
			encodedChars.append(char)
			previousType = charType
		self.encoded: str = "".join(encodedChars)
		self._strToEncoded = strToEncoded
		self._encodedToStr = encodedToStr

	@property
	@override
	def encodedStringLength(self) -> int:
		return len(self.encoded)

	@property
	def insertedCount(self) -> int:
		"""The number of inserted separators."""
		return self.encodedStringLength - self.strLength

	def _strOffsetToEncodedOffset(self, offset: int) -> int:
		if offset >= self.strLength:
			return self.encodedStringLength
		return self._strToEncoded[max(offset, 0)]

	def _encodedOffsetToStrOffset(self, offset: int) -> int:
		if offset >= self.encodedStringLength:
			return self.strLength
		return self._encodedToStr[max(offset, 0)]

	@override
	def strToEncodedOffsets(
		self,
		strStart: int,
		strEnd: int | None = None,
		raiseOnError: bool = False,
	) -> int | tuple[int, int]:
		# Validate the offsets.
		super().strToEncodedOffsets(strStart, strEnd, raiseOnError)
		resultStart = self._strOffsetToEncodedOffset(strStart)
		if strEnd is None:
			return resultStart
		return (resultStart, self._strOffsetToEncodedOffset(strEnd))

	@override
	def encodedToStrOffsets(
		self,
		encodedStart: int,
		encodedEnd: int | None = None,
		raiseOnError: bool = False,
	) -> int | tuple[int, int]:
		# Validate the offsets.
		super().encodedToStrOffsets(encodedStart, encodedEnd, raiseOnError)
		resultStart = self._encodedOffsetToStrOffset(encodedStart)
		if encodedEnd is None:
			return resultStart
		return (resultStart, self._encodedOffsetToStrOffset(encodedEnd))


def getBoundaryTypes(
	boundaries: Collection[addonConfig.SpacingBoundary],
) -> frozenset[frozenset[CharacterType]]:
	return frozenset(boundary.characterTypes for boundary in boundaries)


@cache
def isChineseTable(fileName: str) -> bool:
	"""Whether the given braille table is a Chinese braille table."""
	if fileName.casefold().startswith("zh"):
		return True
	try:
		language = louisHelper.getTableLanguage(fileName)
	except Exception:
		log.debugWarning(f"Unable to get the language of braille table {fileName!r}", exc_info=True)
		return False
	return bool(language) and language.replace("-", "_").split("_")[0].casefold() in _CHINESE_LANGUAGES


_TranslateResult = tuple[list[int], list[int], list[int], int | None]
_originalTranslate: Callable[..., _TranslateResult] | None = None
_active: bool = False
"""Whether spaces should be inserted by :func:`_translate`, ``False`` after :func:`uninstall`."""


def _translate(
	tableList: list[str],
	inbuf: str,
	typeform: Sequence[louisHelper.Typeform] | None = None,
	cursorPos: int | None = None,
	mode: louisHelper.TranslationMode = louisHelper.TranslationMode.NONE,
) -> _TranslateResult:
	"""Replacement for :func:`louisHelper.translate` which inserts spaces at character type boundaries
	before translating to Chinese braille.
	The returned offsets are relative to ``inbuf``, as with the original function.
	"""
	originalTranslate = cast(Callable[..., _TranslateResult], _originalTranslate)
	converter: BoundarySpacingOffsetConverter | None = None
	try:
		boundaries = addonConfig.getSpacingBoundaries() if _active else frozenset()
		if boundaries and tableList and "\0" not in inbuf and isChineseTable(tableList[0]):
			converter = BoundarySpacingOffsetConverter(inbuf, getBoundaryTypes(boundaries))
			if not converter.insertedCount:
				converter = None
	except Exception:
		log.error("Error inserting spaces at character type boundaries", exc_info=True)
		converter = None
	if converter is None:
		return originalTranslate(tableList, inbuf, typeform=typeform, cursorPos=cursorPos, mode=mode)
	if typeform is not None:
		typeform = [
			typeform[cast(int, converter.encodedToStrOffsets(encodedOffset))]
			for encodedOffset in range(converter.encodedStringLength)
		]
	if cursorPos is not None:
		cursorPos = cast(int, converter.strToEncodedOffsets(cursorPos))
	cells, brailleToRawPos, rawToBraillePos, brailleCursorPos = originalTranslate(
		tableList,
		converter.encoded,
		typeform=typeform,
		cursorPos=cursorPos,
		mode=mode,
	)
	# Convert liblouis offsets back to offsets in the text before spaces were inserted.
	brailleToRawPos = [cast(int, converter.encodedToStrOffsets(pos)) for pos in brailleToRawPos]
	rawToBraillePos = [
		rawToBraillePos[cast(int, converter.strToEncodedOffsets(pos))] for pos in range(converter.strLength)
	]
	return cells, brailleToRawPos, rawToBraillePos, brailleCursorPos


def install() -> None:
	global _originalTranslate, _active
	if _originalTranslate is None:
		_originalTranslate = louisHelper.translate
		louisHelper.translate = _translate
	_active = True


def uninstall() -> None:
	global _originalTranslate, _active
	_active = False
	isChineseTable.cache_clear()
	if _originalTranslate is None:
		return
	if louisHelper.translate is _translate:
		louisHelper.translate = _originalTranslate
		_originalTranslate = None
	else:
		# Another component wrapped louisHelper.translate after us.
		# Keep our function in the chain, it passes everything through while inactive.
		log.debugWarning(
			"louisHelper.translate was wrapped by another component, leaving pass-through in place"
		)

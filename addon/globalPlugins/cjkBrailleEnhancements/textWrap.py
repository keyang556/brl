# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Text wrap behaviours for continuous CJK text on braille displays.

See https://github.com/nvaccess/nvda/issues/18295.
Chinese text does not contain spaces between words,
so NVDA's "at word boundaries" text wrap often leaves large parts of a row empty.
Each Han character is translated into several braille cells,
so wrapping without regard to characters splits characters across windows.

This module changes how :class:`braille.buffers.BrailleBuffer` splits its window into rows
when a row would end inside continuous CJK text:

* :attr:`CJKTextWrap.NO_WRAP`: fill the row up to the display edge.
* :attr:`CJKTextWrap.CHARACTER_BOUNDARIES`: every CJK character boundary is a wrap opportunity,
	a character that does not fit completely is moved to the next row.
* :attr:`CJKTextWrap.OVERLAP`: fill the row up to the display edge (GMouse style).
	When a character is split, the next row or window starts again at the first cell of that character.

Boundaries between CJK characters and other text are also used as wrap opportunities
when NVDA wraps text at word boundaries, so that mixed Chinese and English (e.g. UEB) text wraps well.
In all other cases, NVDA's own text wrap setting is applied unchanged.
"""

from collections.abc import Callable
from typing import Any, cast

import config
from braille.buffers import BrailleBuffer, _WindowRowPositions
from braille.constants import CONTEXTPRES_CHANGEDCONTEXT, TEXT_SEPARATOR
from braille.formatting import getParagraphStartMarker
from config.featureFlagEnums import BrailleTextWrapFlag
from logHandler import log

from . import addonConfig
from .addonConfig import CJKTextWrap
from .characters import isContinuousScript

_WORD_WRAP_MODES = (
	BrailleTextWrapFlag.AT_WORD_BOUNDARIES,
	BrailleTextWrapFlag.AT_WORD_OR_SYLLABLE_BOUNDARIES,
)
"""NVDA text wrap modes which avoid splitting words."""

_NEXT_WINDOW_START_ATTR = "_cjkBrailleNextWindowStart"
"""Name of the buffer attribute holding the start of the next window, see :func:`_nextWindow`."""


class _CJKContext:
	"""Lazily maps braille buffer positions to the raw characters they represent."""

	def __init__(self, buffer: BrailleBuffer):
		super().__init__()
		self._buffer = buffer
		self._brailleToRawPos: list[int] | None = None

	@property
	def brailleToRawPos(self) -> list[int]:
		if self._brailleToRawPos is None:
			self._brailleToRawPos = self._buffer.brailleToRawPos
		return self._brailleToRawPos

	def rawPos(self, braillePos: int) -> int | None:
		"""The position in the raw text of the character represented by the cell at ``braillePos``."""
		try:
			return self.brailleToRawPos[braillePos]
		except IndexError:
			return None

	def isCJKRawPos(self, rawPos: int | None) -> bool:
		if rawPos is None:
			return False
		try:
			return isContinuousScript(self._buffer.rawText[rawPos])
		except IndexError:
			return False

	def isCJKCell(self, braillePos: int) -> bool:
		"""Whether the cell at ``braillePos`` represents a CJK character."""
		return self.isCJKRawPos(self.rawPos(braillePos))

	def isMidCJKCharacter(self, braillePos: int) -> bool:
		"""Whether the cells before and at ``braillePos`` both belong to the same CJK character."""
		if braillePos <= 0:
			return False
		rawPos = self.rawPos(braillePos)
		return rawPos is not None and rawPos == self.rawPos(braillePos - 1) and self.isCJKRawPos(rawPos)

	def isCJKBoundary(self, braillePos: int) -> bool:
		"""Whether a row may start at ``braillePos`` because it is a boundary of a CJK character,
		i.e. the cells before and at ``braillePos`` represent different characters,
		at least one of which is a CJK character.
		"""
		if braillePos <= 0:
			return False
		cells = self._buffer.brailleCells
		if not (cells[braillePos - 1] and cells[braillePos]):
			# Spaces are handled by NVDA.
			return False
		before = self.rawPos(braillePos - 1)
		after = self.rawPos(braillePos)
		if before is None or after is None or before == after:
			return False
		return self.isCJKRawPos(before) or self.isCJKRawPos(after)

	def characterStart(self, braillePos: int, minPos: int) -> int:
		"""The first cell (not before ``minPos``) of the character represented by the cell at ``braillePos``."""
		rawPos = self.rawPos(braillePos)
		while braillePos > minPos and self.rawPos(braillePos - 1) == rawPos:
			braillePos -= 1
		return braillePos

	def characterEnd(self, braillePos: int, maxPos: int) -> int:
		"""The position after the last cell (not after ``maxPos``) of the character at ``braillePos``."""
		rawPos = self.rawPos(braillePos)
		while braillePos < maxPos and self.rawPos(braillePos) == rawPos:
			braillePos += 1
		return braillePos

	def lastCJKBoundary(self, start: int, end: int) -> int | None:
		"""The last CJK character boundary in the range (start, end), ``None`` if there is none."""
		for pos in range(end - 1, start, -1):
			if self.isCJKBoundary(pos):
				return pos
		return None


_original_calculateWindowRowBufferOffsets: Any = None
"""The original :meth:`BrailleBuffer._calculateWindowRowBufferOffsets`, ``None`` when not installed."""
_original_nextWindow: Any = None
"""The original :meth:`BrailleBuffer._nextWindow`, ``None`` when not installed."""
_originalWindowEndPos: property | None = None
"""The original :attr:`BrailleBuffer.windowEndPos` property, ``None`` when not installed."""


def _callOriginalCalculate(buffer: BrailleBuffer, pos: int) -> None:
	cast(Callable[[BrailleBuffer, int], None], _original_calculateWindowRowBufferOffsets)(buffer, pos)


def _brailleConf() -> Any:
	"""NVDA's braille configuration section (``config.conf`` is not typed)."""
	return cast(Any, config.conf)["braille"]


def _getTextWrap() -> BrailleTextWrapFlag:
	return _brailleConf()["textWrap"].calculated()


def _calculateRow(
	buffer: BrailleBuffer,
	ctx: _CJKContext,
	start: int,
	mode: CJKTextWrap,
	textWrap: BrailleTextWrapFlag,
) -> tuple[_WindowRowPositions, int]:
	"""Calculate a single row of the braille window.

	:param start: The start of the row in the braille buffer.
	:return: The row and the buffer position where the next row should start.
	"""
	# NVDA's own calculation of a row only depends on the start of that row,
	# so the first row NVDA calculates for this start is NVDA's result for this row.
	_callOriginalCalculate(buffer, start)
	nvdaRow = buffer._windowRowBufferOffsets[0]
	cells = buffer.brailleCells
	bufferEnd = len(cells)
	edge = start + buffer.handler.displayDimensions.numCols
	if edge >= bufferEnd or not (cells[edge - 1] and cells[edge]):
		# The rest of the buffer fits on the row, or the row ends at a space.
		return nvdaRow, nvdaRow.end
	if ctx.isMidCJKCharacter(edge):
		# The display edge splits a CJK character.
		charStart = ctx.characterStart(edge, start)
		match mode:
			case CJKTextWrap.NO_WRAP:
				if textWrap == BrailleTextWrapFlag.NONE:
					return _WindowRowPositions(start, edge), edge
				# As in NVDA, the continuation mark is shown when a word is cut,
				# except when text wrap is off.
				return _WindowRowPositions(start, edge - 1, True), edge - 1
			case CJKTextWrap.CHARACTER_BOUNDARIES if charStart > start:
				return _WindowRowPositions(start, charStart), charStart
			case CJKTextWrap.OVERLAP if charStart > start:
				return _WindowRowPositions(start, edge), charStart
			case _:
				# The character is wider than the row.
				return nvdaRow, nvdaRow.end
	if ctx.isCJKBoundary(edge):
		# The display edge is at the boundary of a CJK character, the row can end here.
		return _WindowRowPositions(start, edge), edge
	# The display edge is inside text other than CJK text, e.g. an English word.
	if textWrap in _WORD_WRAP_MODES:
		# Treat boundaries of CJK characters like spaces.
		lastBoundary = ctx.lastCJKBoundary(start, edge)
		if (
			lastBoundary is not None
			and (
				lastBoundary >= nvdaRow.end
				# NVDA cut the word at the display edge as there is no space on the row.
				or (nvdaRow.showContinuationMark and 0 not in cells[start : edge + 1])
			)
		):
			return _WindowRowPositions(start, lastBoundary), lastBoundary
	return nvdaRow, nvdaRow.end


def _calculateWindowRowBufferOffsets(self: BrailleBuffer, pos: int) -> None:
	"""Replacement for :meth:`BrailleBuffer._calculateWindowRowBufferOffsets`."""
	mode = addonConfig.getTextWrap()
	setattr(self, _NEXT_WINDOW_START_ATTR, None)
	if mode == CJKTextWrap.FOLLOW_NVDA or not self.brailleCells:
		_callOriginalCalculate(self, pos)
		return
	try:
		textWrap = _getTextWrap()
		ctx = _CJKContext(self)
		bufferEnd = len(self.brailleCells)
		numCols = self.handler.displayDimensions.numCols
		rows: list[_WindowRowPositions] = []
		start = pos
		nextStart = pos
		for _row in range(self.handler.displayDimensions.numRows):
			row, nextStart = _calculateRow(self, ctx, start, mode, textWrap)
			rows.append(row)
			if start + numCols > bufferEnd:
				# This row contains the end of the buffer.
				break
			start = nextStart
	except Exception:
		log.error("Error calculating braille window rows for CJK text", exc_info=True)
		_callOriginalCalculate(self, pos)
		return
	self._windowRowBufferOffsets = rows
	setattr(self, _NEXT_WINDOW_START_ATTR, nextStart)


def _findWindowStart(
	self: BrailleBuffer,
	ctx: _CJKContext,
	startPos: int,
	endPos: int,
	mode: CJKTextWrap,
	textWrap: BrailleTextWrapFlag,
) -> int:
	"""Find the start of a window which should end at ``endPos``, not before ``startPos``."""
	cells = self.brailleCells
	if textWrap not in _WORD_WRAP_MODES:
		if mode != CJKTextWrap.NO_WRAP and ctx.isMidCJKCharacter(startPos):
			# Don't start the window in the middle of a CJK character.
			return ctx.characterEnd(startPos, endPos)
		return startPos
	# Try not to split words across windows, as NVDA does,
	# but also allow the window to start at CJK character boundaries.
	pos = startPos
	while pos < endPos:
		if cells[pos - 1] == 0:
			# Start after a block of spaces.
			while pos < endPos and cells[pos] == 0:
				pos += 1
			return pos
		if ctx.isCJKBoundary(pos):
			return pos
		if mode == CJKTextWrap.NO_WRAP and ctx.isCJKCell(pos):
			return pos
		pos += 1
	return startPos


def _set_windowEndPos(self: BrailleBuffer, endPos: int) -> None:
	"""Replacement for the setter of :attr:`BrailleBuffer.windowEndPos`.

	This follows NVDA's implementation,
	except for the way the window start is chosen to avoid splitting words or CJK characters.
	"""
	mode = addonConfig.getTextWrap()
	originalSetter = cast(Callable[[BrailleBuffer, int], None], cast(property, _originalWindowEndPos).fset)
	if mode == CJKTextWrap.FOLLOW_NVDA:
		originalSetter(self, endPos)
		return
	try:
		# Auto properties of BrailleBuffer, such as regionsWithPositions, are not known to type checkers.
		buffer: Any = self
		startPos = endPos - self.handler.displaySize
		# Loop through the currently displayed regions in reverse order
		# If focusToHardLeft is set for one of the regions, the display shouldn't scroll further back than the start of that region
		for region, regionStart, _regionEnd in reversed(list(buffer.regionsWithPositions)):
			if regionStart < endPos:
				if region.focusToHardLeft:
					# Only scroll to the start of this region.
					restrictPos = regionStart
					break
				elif _brailleConf()["focusContextPresentation"] != CONTEXTPRES_CHANGEDCONTEXT:
					# We aren't currently dealing with context change presentation
					# thus, we only need to consider the last region
					# since it doesn't have focusToHardLeftSet, the window start position isn't restricted
					restrictPos = 0
					break
		else:
			restrictPos = 0
		if startPos <= restrictPos:
			self.windowStartPos = restrictPos
			return
		textWrap = _getTextWrap()
		startPos = _findWindowStart(self, _CJKContext(self), startPos, endPos, mode, textWrap)
		if textWrap in _WORD_WRAP_MODES:
			# When text wrap is enabled, the first block of spaces may be removed from the current window.
			# This may prevent displaying the start of paragraphs.
			paragraphStartMarker = getParagraphStartMarker()
			if paragraphStartMarker and self.regions[-1].rawText.startswith(
				paragraphStartMarker + TEXT_SEPARATOR,
			):
				region, regionStart, _regionEnd = list(buffer.regionsWithPositions)[-1]
				# Show paragraph start indicator if it is now at the left of the current braille window
				if startPos <= len(paragraphStartMarker) + 1:
					startPos = self.regionPosToBufferPos(region, regionStart)
	except Exception:
		log.error("Error calculating braille window start for CJK text", exc_info=True)
		originalSetter(self, endPos)
		return
	self.windowStartPos = startPos


def _nextWindow(self: BrailleBuffer) -> bool:
	"""Replacement for :meth:`BrailleBuffer._nextWindow`.

	When a CJK character is split at the end of the window in :attr:`CJKTextWrap.OVERLAP` mode,
	the next window starts at the first cell of that character.
	"""
	originalNextWindow = cast(Callable[[BrailleBuffer], bool], _original_nextWindow)
	nextStart: int | None = getattr(self, _NEXT_WINDOW_START_ATTR, None)
	if nextStart is None:
		return originalNextWindow(self)
	oldStart = self.windowStartPos
	end = self.windowEndPos
	if end < len(self.brailleCells):
		self.windowStartPos = nextStart if oldStart < nextStart < end else end
	return self.windowStartPos != oldStart


def install() -> bool:
	"""Install the CJK text wrap behaviours.

	:return: Whether installation succeeded.
	"""
	global _original_calculateWindowRowBufferOffsets, _original_nextWindow, _originalWindowEndPos
	if _originalWindowEndPos is not None:
		return True
	windowEndPos: Any = BrailleBuffer.__dict__.get("windowEndPos")
	calculate: Any = BrailleBuffer.__dict__.get("_calculateWindowRowBufferOffsets")
	nextWindow: Any = BrailleBuffer.__dict__.get("_nextWindow")
	if not (isinstance(windowEndPos, property) and callable(calculate) and callable(nextWindow)):
		log.error("Unsupported BrailleBuffer implementation, CJK text wrap is unavailable")
		return False
	_original_calculateWindowRowBufferOffsets = calculate
	_original_nextWindow = nextWindow
	_originalWindowEndPos = windowEndPos
	setattr(BrailleBuffer, "_calculateWindowRowBufferOffsets", _calculateWindowRowBufferOffsets)
	setattr(BrailleBuffer, "_nextWindow", _nextWindow)
	setattr(BrailleBuffer, "windowEndPos", property(windowEndPos.fget, _set_windowEndPos, windowEndPos.fdel))
	return True


def uninstall() -> None:
	global _original_calculateWindowRowBufferOffsets, _original_nextWindow, _originalWindowEndPos
	if _originalWindowEndPos is None:
		return
	setattr(BrailleBuffer, "_calculateWindowRowBufferOffsets", _original_calculateWindowRowBufferOffsets)
	setattr(BrailleBuffer, "_nextWindow", _original_nextWindow)
	setattr(BrailleBuffer, "windowEndPos", _originalWindowEndPos)
	_original_calculateWindowRowBufferOffsets = None
	_original_nextWindow = None
	_originalWindowEndPos = None

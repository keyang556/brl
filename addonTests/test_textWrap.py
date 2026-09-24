# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Tests for CJK text wrap (NVDA issue 18295)."""

import unittest

import braille
import braille.buffers
import braille.display
import braille.extensions
import brailleTables
import config
from braille.buffers import BrailleBuffer, _WindowRowPositions
from braille.regions.base import TextRegion
from cjkBrailleEnhancements import addonConfig, textWrap
from cjkBrailleEnhancements.addonConfig import CJKTextWrap
from config.featureFlag import FeatureFlag
from config.featureFlagEnums import BrailleTextWrapFlag

CHINESE = "這是一個測試，我們使用螢幕閱讀器閱讀中文點字。"
MIXED = "這是一個測試，我們使用NVDA screen reader閱讀中文點字"
ENGLISH = "The quick brown fox jumps over the lazy dog and keeps running far away"

_numRows = 1
_numCols = 20


def _getDisplayDimensions(dimensions: braille.display.DisplayDimensions) -> braille.display.DisplayDimensions:
	return braille.display.DisplayDimensions(numRows=_numRows, numCols=_numCols)


def _setTextWrap(mode: BrailleTextWrapFlag) -> None:
	behaviorOfDefault = (
		BrailleTextWrapFlag.AT_WORD_BOUNDARIES
		if mode != BrailleTextWrapFlag.AT_WORD_BOUNDARIES
		else BrailleTextWrapFlag.MARK_WORD_CUTS
	)
	config.conf["braille"]["textWrap"] = FeatureFlag(mode, behaviorOfDefault)


class _TextWrapTestCase(unittest.TestCase):
	def setUp(self):
		global _numRows, _numCols
		_numRows, _numCols = 1, 20
		addonConfig.register()
		braille.extensions.filter_displayDimensions.register(_getDisplayDimensions)
		self._oldTable = braille.handler.table
		braille.handler.table = brailleTables.getTable("zh-tw.ctb")
		self.assertTrue(textWrap.install())
		self.buffer = braille.handler.mainBuffer

	def tearDown(self):
		textWrap.uninstall()
		addonConfig.setTextWrap(CJKTextWrap.FOLLOW_NVDA)
		_setTextWrap(BrailleTextWrapFlag.NONE)
		self.buffer.clear()
		braille.handler.table = self._oldTable
		braille.extensions.filter_displayDimensions.unregister(_getDisplayDimensions)

	def setText(self, text: str) -> None:
		self.buffer.clear()
		region = TextRegion(text)
		region.update()
		self.buffer.regions.append(region)
		self.buffer.update()
		self.buffer.windowStartPos = 0
		self.brailleToRawPos = self.buffer.brailleToRawPos

	def rawPos(self, braillePos: int) -> int:
		return self.brailleToRawPos[braillePos]

	def isCharacterBoundary(self, braillePos: int) -> bool:
		return braillePos in (0, len(self.buffer.brailleCells)) or self.rawPos(braillePos - 1) != self.rawPos(
			braillePos
		)

	def isBreak(self, braillePos: int) -> bool:
		"""Whether a row may end at ``braillePos``: a character boundary or next to a space."""
		cells = self.buffer.brailleCells
		return self.isCharacterBoundary(braillePos) or cells[braillePos] == 0 or cells[braillePos - 1] == 0

	def characterStart(self, braillePos: int) -> int:
		while braillePos > 0 and self.rawPos(braillePos - 1) == self.rawPos(braillePos):
			braillePos -= 1
		return braillePos

	def firstSplitStart(self, text: str) -> int:
		"""Find a window start at which the display edge splits a Chinese character."""
		self.setText(text)
		for start in range(len(self.buffer.brailleCells) - _numCols):
			edge = start + _numCols
			if (
				start == self.characterStart(start)
				and not self.isCharacterBoundary(edge)
				and all(self.buffer.brailleCells[edge - 1 : edge + 1])
			):
				return start
		self.fail("No split character found")

	def originalRows(self, pos: int) -> list[_WindowRowPositions]:
		assert textWrap._original_calculateWindowRowBufferOffsets is not None
		textWrap._original_calculateWindowRowBufferOffsets(self.buffer, pos)
		return list(self.buffer._windowRowBufferOffsets)

	def rows(self, pos: int) -> list[_WindowRowPositions]:
		self.buffer.windowStartPos = pos
		return list(self.buffer._windowRowBufferOffsets)


class TestInstall(_TextWrapTestCase):
	def test_uninstallRestoresBrailleBuffer(self):
		windowEndPos = textWrap._originalWindowEndPos
		textWrap.uninstall()
		self.assertIs(BrailleBuffer.__dict__["windowEndPos"], windowEndPos)
		self.assertIsNot(BrailleBuffer._nextWindow, textWrap._nextWindow)
		self.assertIsNot(
			BrailleBuffer._calculateWindowRowBufferOffsets, textWrap._calculateWindowRowBufferOffsets
		)
		self.assertTrue(textWrap.install())
		self.assertIs(BrailleBuffer._nextWindow, textWrap._nextWindow)


class TestFollowNVDA(_TextWrapTestCase):
	def test_sameAsNVDA(self):
		for flag in BrailleTextWrapFlag:
			if flag == BrailleTextWrapFlag.DEFAULT:
				continue
			_setTextWrap(flag)
			for text in (CHINESE, MIXED, ENGLISH):
				self.setText(text)
				for pos in range(len(self.buffer.brailleCells)):
					self.assertEqual(self.rows(pos), self.originalRows(pos), msg=f"{flag} {text} {pos}")


class TestNonCJKText(_TextWrapTestCase):
	def test_englishUnchanged(self):
		"""Text without CJK characters wraps exactly as in NVDA."""
		braille.handler.table = brailleTables.getTable("en-ueb-g1.ctb")
		for mode in CJKTextWrap:
			addonConfig.setTextWrap(mode)
			for flag in BrailleTextWrapFlag:
				if flag == BrailleTextWrapFlag.DEFAULT:
					continue
				_setTextWrap(flag)
				self.setText(ENGLISH)
				for pos in range(len(self.buffer.brailleCells)):
					self.assertEqual(self.rows(pos), self.originalRows(pos), msg=f"{mode} {flag} {pos}")


class TestCharacterBoundaries(_TextWrapTestCase):
	def test_wordWrapUsesCharacterBoundaries(self):
		"""With NVDA wrapping at word boundaries, Chinese text no longer leaves most of the row empty."""
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		addonConfig.setTextWrap(CJKTextWrap.CHARACTER_BOUNDARIES)
		self.setText(CHINESE)
		pos = 0
		while pos < len(self.buffer.brailleCells):
			row = self.rows(pos)[0]
			self.assertTrue(self.isBreak(row.end) or row.end == len(self.buffer.brailleCells), msg=row)
			self.assertFalse(row.showContinuationMark)
			if row.end < len(self.buffer.brailleCells) and self.isCharacterBoundary(row.end):
				# The next character doesn't fit on the row, so the row is as long as possible.
				nextCharEnd = row.end + 1
				while not self.isCharacterBoundary(nextCharEnd):
					nextCharEnd += 1
				self.assertGreater(nextCharEnd, pos + _numCols, msg=row)
			pos = row.end

	def test_splitCharacterMovedToNextRow(self):
		addonConfig.setTextWrap(CJKTextWrap.CHARACTER_BOUNDARIES)
		for flag in (BrailleTextWrapFlag.NONE, BrailleTextWrapFlag.MARK_WORD_CUTS):
			_setTextWrap(flag)
			start = self.firstSplitStart(CHINESE)
			edge = start + _numCols
			row = self.rows(start)[0]
			self.assertEqual(row, _WindowRowPositions(start, self.characterStart(edge)))

	def test_multipleRows(self):
		global _numRows
		_numRows = 3
		_setTextWrap(BrailleTextWrapFlag.NONE)
		addonConfig.setTextWrap(CJKTextWrap.CHARACTER_BOUNDARIES)
		self.setText(CHINESE)
		rows = self.rows(0)
		self.assertEqual(len(rows), 3)
		for previous, row in zip(rows, rows[1:]):
			self.assertEqual(previous.end, row.start)
		for row in rows:
			self.assertTrue(
				self.isBreak(row.end), msg=(row, self.buffer.brailleCells[row.end - 1 : row.end + 1])
			)
			self.assertLessEqual(row.end - row.start, _numCols)

	def test_mixedTextWrapsBeforeLatinWord(self):
		"""A Latin word following Chinese text is wrapped at the Chinese character boundary."""
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		addonConfig.setTextWrap(CJKTextWrap.CHARACTER_BOUNDARIES)
		self.setText(MIXED)
		rawToBraillePos = self.buffer.rawToBraillePos
		nStart = rawToBraillePos[MIXED.index("N")]
		# Start the window so that the display edge falls inside "NVDA".
		start = nStart + 2 - _numCols
		self.assertGreaterEqual(start, 0)
		row = self.rows(start)[0]
		self.assertEqual(row.end, nStart)
		self.assertFalse(row.showContinuationMark)

	def test_scrollBackStartsAtCharacterBoundary(self):
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		addonConfig.setTextWrap(CJKTextWrap.CHARACTER_BOUNDARIES)
		self.setText(CHINESE)
		end = len(self.buffer.brailleCells) - 5
		end = self.characterStart(end)
		self.buffer.windowEndPos = end
		start = self.buffer.windowStartPos
		self.assertTrue(self.isBreak(start))
		self.assertLessEqual(end - start, _numCols)
		# Without the add-on, NVDA can only scroll to after a space, far from the display edge.
		self.assertLessEqual(start, end - _numCols + 2)

	def test_scrollForwardAndBackRoundTrip(self):
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		addonConfig.setTextWrap(CJKTextWrap.CHARACTER_BOUNDARIES)
		self.setText(CHINESE)
		starts = [self.buffer.windowStartPos]
		while self.buffer._nextWindow():
			starts.append(self.buffer.windowStartPos)
			self.assertTrue(self.isBreak(self.buffer.windowStartPos))
		self.assertGreater(len(starts), 2)
		self.assertEqual(self.buffer.windowEndPos, len(self.buffer.brailleCells))
		while self.buffer._previousWindow():
			self.assertTrue(self.isBreak(self.buffer.windowStartPos))
		self.assertEqual(self.buffer.windowStartPos, 0)


class TestOverlap(_TextWrapTestCase):
	def test_rowFilledAndNextWindowRepeatsCharacter(self):
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		addonConfig.setTextWrap(CJKTextWrap.OVERLAP)
		start = self.firstSplitStart(CHINESE)
		edge = start + _numCols
		self.assertEqual(self.rows(start), [_WindowRowPositions(start, edge)])
		self.assertTrue(self.buffer._nextWindow())
		self.assertEqual(self.buffer.windowStartPos, self.characterStart(edge))

	def test_multipleRowsOverlap(self):
		global _numRows
		_numRows = 2
		_setTextWrap(BrailleTextWrapFlag.NONE)
		addonConfig.setTextWrap(CJKTextWrap.OVERLAP)
		start = self.firstSplitStart(CHINESE)
		edge = start + _numCols
		rows = self.rows(start)
		self.assertEqual(rows[0], _WindowRowPositions(start, edge))
		self.assertEqual(rows[1].start, self.characterStart(edge))

	def test_scrollingReachesEnd(self):
		_setTextWrap(BrailleTextWrapFlag.NONE)
		addonConfig.setTextWrap(CJKTextWrap.OVERLAP)
		self.setText(CHINESE * 3)
		count = 0
		while self.buffer._nextWindow():
			count += 1
			self.assertTrue(self.isBreak(self.buffer.windowStartPos))
			self.assertLess(count, 1000)
		self.assertEqual(self.buffer.windowEndPos, len(self.buffer.brailleCells))
		while self.buffer._previousWindow():
			count -= 1
			self.assertTrue(self.isBreak(self.buffer.windowStartPos))
			self.assertGreater(count, -1000)
		self.assertEqual(self.buffer.windowStartPos, 0)


class TestNoWrap(_TextWrapTestCase):
	def test_fillsRow(self):
		addonConfig.setTextWrap(CJKTextWrap.NO_WRAP)
		_setTextWrap(BrailleTextWrapFlag.NONE)
		start = self.firstSplitStart(CHINESE)
		self.assertEqual(self.rows(start), [_WindowRowPositions(start, start + _numCols)])

	def test_continuationMarkAsInNVDA(self):
		addonConfig.setTextWrap(CJKTextWrap.NO_WRAP)
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		start = self.firstSplitStart(CHINESE)
		self.assertEqual(self.rows(start), [_WindowRowPositions(start, start + _numCols - 1, True)])

	def test_boundaryAtEdge(self):
		"""When the display edge is at a character boundary, the whole row is used."""
		addonConfig.setTextWrap(CJKTextWrap.NO_WRAP)
		_setTextWrap(BrailleTextWrapFlag.AT_WORD_BOUNDARIES)
		self.setText(CHINESE)
		for start in range(len(self.buffer.brailleCells) - _numCols):
			edge = start + _numCols
			if self.isCharacterBoundary(edge) and all(self.buffer.brailleCells[edge - 1 : edge + 1]):
				self.assertEqual(self.rows(start), [_WindowRowPositions(start, edge)])
				return
		self.fail("No character boundary found")

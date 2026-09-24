# A part of the CJK Braille Enhancements add-on for NVDA
# Copyright (C) 2026 Keyang556
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Configuration of the add-on."""

from typing import Any, cast, override

import addonHandler
import config
from utils.displayString import DisplayStringStrEnum

from .characters import CharacterType

addonHandler.initTranslation()

SECTION = "cjkBrailleEnhancements"
"""The name of the configuration section of this add-on."""


class CJKTextWrap(DisplayStringStrEnum):
	"""How to wrap continuous CJK text when it does not fit on a row of the braille display."""

	FOLLOW_NVDA = "followNVDA"
	"""Use NVDA's text wrap setting unchanged."""
	NO_WRAP = "noWrap"
	"""Never wrap CJK text, fill the row up to the display edge."""
	CHARACTER_BOUNDARIES = "characterBoundaries"
	"""Wrap at the boundaries of CJK characters, never split a character."""
	OVERLAP = "overlap"
	"""Use every cell; a character split at the display edge is shown again in full on the next window."""

	@property
	@override
	def _displayStringLabels(self) -> dict["CJKTextWrap", str]:
		return {
			# Translators: A choice for the CJK text wrap setting.
			self.FOLLOW_NVDA: _("Same as NVDA text wrap"),
			# Translators: A choice for the CJK text wrap setting.
			self.NO_WRAP: _("Off (fill the display, split characters)"),
			# Translators: A choice for the CJK text wrap setting.
			self.CHARACTER_BOUNDARIES: _("At character boundaries"),
			# Translators: A choice for the CJK text wrap setting.
			self.OVERLAP: _("Repeat split character on next window (GMouse style)"),
		}


class SpacingBoundary(DisplayStringStrEnum):
	"""Character type boundaries at which a space can be inserted before braille translation."""

	CHINESE_LATIN = "spaceBetweenChineseAndLatin"
	CHINESE_NUMBER = "spaceBetweenChineseAndNumbers"
	LATIN_NUMBER = "spaceBetweenLatinAndNumbers"

	@property
	@override
	def _displayStringLabels(self) -> dict["SpacingBoundary", str]:
		return {
			# Translators: An item in the list of boundaries where spaces are inserted in Chinese braille.
			self.CHINESE_LATIN: _("Between Chinese characters and Latin letters"),
			# Translators: An item in the list of boundaries where spaces are inserted in Chinese braille.
			self.CHINESE_NUMBER: _("Between Chinese characters and numbers"),
			# Translators: An item in the list of boundaries where spaces are inserted in Chinese braille.
			self.LATIN_NUMBER: _("Between Latin letters and numbers"),
		}

	@property
	def characterTypes(self) -> frozenset[CharacterType]:
		"""The pair of character types this boundary separates."""
		match self:
			case SpacingBoundary.CHINESE_LATIN:
				return frozenset((CharacterType.CHINESE, CharacterType.LATIN))
			case SpacingBoundary.CHINESE_NUMBER:
				return frozenset((CharacterType.CHINESE, CharacterType.NUMBER))
			case SpacingBoundary.LATIN_NUMBER:
				return frozenset((CharacterType.LATIN, CharacterType.NUMBER))


CONF_SPEC: dict[str, str] = {
	"textWrap": 'option({}, default="{}")'.format(
		", ".join(f'"{mode.value}"' for mode in CJKTextWrap),
		CJKTextWrap.FOLLOW_NVDA.value,
	),
	"insertSpaces": "boolean(default=false)",
	SpacingBoundary.CHINESE_LATIN.value: "boolean(default=true)",
	SpacingBoundary.CHINESE_NUMBER.value: "boolean(default=true)",
	SpacingBoundary.LATIN_NUMBER.value: "boolean(default=false)",
}
"""Configuration specification of this add-on, registered as ``config.conf.spec[SECTION]``."""


def register() -> None:
	config.conf.spec[SECTION] = CONF_SPEC


def _section() -> Any:
	"""The configuration section of this add-on (``config.conf`` is not typed)."""
	return cast(Any, config.conf)[SECTION]


def getTextWrap() -> CJKTextWrap:
	try:
		return CJKTextWrap(_section()["textWrap"])
	except (KeyError, ValueError):
		return CJKTextWrap.FOLLOW_NVDA


def setTextWrap(mode: CJKTextWrap) -> None:
	_section()["textWrap"] = mode.value


def isSpacingEnabled() -> bool:
	try:
		return bool(_section()["insertSpaces"])
	except KeyError:
		return False


def setSpacingEnabled(enabled: bool) -> None:
	_section()["insertSpaces"] = enabled


def isSpacingBoundaryEnabled(boundary: SpacingBoundary) -> bool:
	"""Whether the given boundary is selected, regardless of whether spacing is enabled."""
	return bool(_section()[boundary.value])


def getSpacingBoundaries() -> frozenset[SpacingBoundary]:
	"""The boundaries at which spaces should be inserted, empty when spacing is disabled."""
	if not isSpacingEnabled():
		return frozenset()
	return frozenset(boundary for boundary in SpacingBoundary if isSpacingBoundaryEnabled(boundary))


def setSpacingBoundary(boundary: SpacingBoundary, enabled: bool) -> None:
	_section()[boundary.value] = enabled

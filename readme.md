# CJK Braille Enhancements

This NVDA add-on improves braille output for continuous script text such as Chinese.
It implements the behaviours requested in the following NVDA issues:

* [#18295: Redefine wordWrap behavior for continuous script languages](https://github.com/nvaccess/nvda/issues/18295), including the behaviours proposed in its comments.
* [#20726: Add optional spacing between Chinese text, Latin letters, and numbers in Chinese braille output](https://github.com/nvaccess/nvda/issues/20726).

Requires NVDA 2026.3 or later.

## Settings

The settings are found in the "CJK Braille" category of NVDA's settings dialog (NVDA menu, Preferences, Settings).
They are saved in the current configuration profile.

### Text wrap for CJK characters

Chinese text doesn't contain spaces between words, and each Chinese character is translated into several braille cells.
With NVDA's "At word boundaries" text wrap, a long run of Chinese text is moved to the next window as a whole, often leaving more than 20 empty cells.
With text wrap off, a character may be split, with its first cells at the end of one window and the remaining cells at the start of the next.

This setting controls what happens when a row of the braille display ends inside CJK text (Han characters, Bopomofo, Kana, CJK punctuation and full width forms).
Other text, such as English words, continues to follow NVDA's own "Text wrap" setting in the Braille category.

| Option | Behaviour |
|---|---|
| Same as NVDA text wrap (default) | NVDA's behaviour is not changed. |
| Off (fill the display, split characters) | CJK text fills the row up to the display edge, even when that splits a character. As in NVDA, the continuation mark (dots 7-8) is shown at the end of the row when a character is split, unless NVDA's text wrap is set to "Off". |
| At character boundaries | The boundary between any two CJK characters is a wrap opportunity. A character that doesn't fit completely on the row is moved to the next row, so no more than a few cells stay empty. |
| Repeat split character on next window (GMouse style) | All cells of the display are used. When a character is split at the display edge, panning forward starts again at the first cell of that character, so the character is shown completely on the next window. |

With the last three options, when NVDA's text wrap is set to "At word boundaries" or "At word or syllable boundaries", the boundary between a CJK character and other text is also treated like a space.
For example, when Chinese braille is mixed with English (UEB) braille, an English word that directly follows Chinese text is moved to the next row as a whole, instead of the row ending at the last space which may be far away.

The same rules are used when panning backward, so the window never starts in the middle of a CJK character, except with "Off".

### Insert spaces between Chinese characters, Latin letters and numbers

When this option is checked, a space is inserted before braille translation wherever the character type changes, for example:

* 使用NVDA閱讀 is shown as 使用 NVDA 閱讀
* 版本2026.3已發布 is shown as 版本 2026.3 已發布

Consecutive Chinese characters are left unchanged: no word segmentation is performed, so 這是一個測試 stays 這是一個測試.
This is independent of NVDA's "Use Chinese word segmentation" setting.
No space is added where there already is one, and punctuation is never separated.

This only applies when the braille output table is a Chinese table.
The inserted spaces only affect braille; the text itself is not changed, and cursor routing works as usual.
Pressing a routing key on an inserted space moves the cursor to the character after it.

In the "Insert spaces at" list, choose the boundaries where spaces are inserted:

* Between Chinese characters and Latin letters (checked by default)
* Between Chinese characters and numbers (checked by default)
* Between Latin letters and numbers (unchecked by default)

This option is off by default.

## Commands

The following commands have no gesture assigned.
You can assign gestures to them in the Braille category of NVDA's Input Gestures dialog.

* Cycle through the braille text wrap modes for CJK characters.
* Toggle inserting spaces between Chinese characters, Latin letters and numbers in braille.

## Changes

### 1.0.0

* Initial release.

/**
 * Server offsets → editor positions, for one exact text.
 *
 * `ductus` is Python, and a Python string is indexed by **code point**: every `Span`
 * it reports counts characters that way. A JavaScript string — and so ProseMirror —
 * counts **UTF-16 code units**, in which every character outside the Basic
 * Multilingual Plane (emoji, many CJK ideographs, mathematical letters) takes two.
 * Treating one count as the other shifts every finding after the first such
 * character by one per character, and can put a highlight boundary in the middle of
 * a surrogate pair (issue #11).
 *
 * The mapping is a property of the text, so it is built from the text the report was
 * computed against — at the one instant, in `track`, when that text and the editor's
 * text are the same. Every later edit moves positions through ProseMirror's own
 * `Mapping`, which already speaks UTF-16, so nothing after this needs converting.
 */

/** Plain-text UTF-16 index → ProseMirror position. The one wrapper node costs 1. */
const WRAPPER = 1

/** Any UTF-16 high surrogate: the text holds at least one astral character. */
const HIGH_SURROGATE = /[\uD800-\uDBFF]/

/**
 * A function from a Python code-point offset into `text` to a ProseMirror position.
 *
 * Text with no astral character — nearly all of it — needs no table: the two counts
 * agree. Otherwise one pass records the UTF-16 index at which each code point starts.
 * An offset past the end (never produced by the server) clamps to the end rather than
 * inventing a position the document does not have.
 */
export function positionsIn(text: string): (offset: number) => number {
  if (!HIGH_SURROGATE.test(text)) return (offset) => offset + WRAPPER
  const unitAt: number[] = []
  let units = 0
  for (const char of text) {
    unitAt.push(units)
    units += char.length
  }
  unitAt.push(units)
  const last = unitAt.length - 1
  return (offset) => unitAt[Math.max(0, Math.min(offset, last))]! + WRAPPER
}

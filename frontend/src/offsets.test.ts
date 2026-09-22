/**
 * Issue #11: a highlight must land on the characters the server quoted, emoji or not.
 */

import { describe, expect, it } from 'vitest'

import { positionsIn } from './offsets'

/** What the editor would show between two server offsets (positions are offset + 1). */
const slice = (text: string, start: number, end: number) => {
  const pos = positionsIn(text)
  return text.slice(pos(start) - 1, pos(end) - 1)
}

/** The substring Python would return for text[start:end]. */
const pySlice = (text: string, start: number, end: number) =>
  Array.from(text).slice(start, end).join('')

describe('positionsIn', () => {
  it('is offset + 1 for text with no astral characters', () => {
    const pos = positionsIn("it's — café, naïve ‘quotes’")
    expect([0, 5, 20].map(pos)).toEqual([1, 6, 21])
  })

  it('lands on the quoted text after emoji (the #11 repro)', () => {
    const text = '😀'.repeat(30) + 'Great question! More.'
    const start = 30 // Python: text.index('Great') == 30
    const end = start + 'Great question'.length
    expect(pySlice(text, start, end)).toBe('Great question')
    expect(slice(text, start, end)).toBe('Great question')
  })

  it('never splits a surrogate pair', () => {
    const text = 'a😀b𝒳c'
    for (let s = 0; s <= 5; s++) {
      for (let e = s; e <= 5; e++) expect(slice(text, s, e)).toBe(pySlice(text, s, e))
    }
  })

  it('maps the end of the text to the end of the document', () => {
    const text = 'x😀'
    expect(positionsIn(text)(2)).toBe(text.length + 1)
  })

  it('clamps an offset past the end instead of inventing a position', () => {
    const text = '😀'
    expect(positionsIn(text)(99)).toBe(text.length + 1)
  })
})

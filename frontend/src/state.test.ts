/**
 * The invalidation policy, tested without an editor or a browser.
 *
 * `applyEdit` takes the position-mapping function as an argument precisely so it can be
 * tested like this: the policy is what matters, and it is separable from ProseMirror.
 * The fake `mapPos` below is a simple insertion model — everything at or after the
 * insertion point moves by `length`, with the bias deciding what happens *exactly at*
 * the boundary, which is the case that had the bug.
 */

import { describe, expect, it } from 'vitest'

import { allUnverified, applyEdit, isStale, track, type State } from './state'
import type { Report, Segment, Signal, Span } from './generated/report'

const span = (start: number, end: number, quote = 'q'): Span => ({
  start, end, quote, prefix: '', suffix: '', level: 'token',
})

const signal = (name: string, s: number, e: number): Signal => ({
  name, direction: 'machine', weight: 0.3, detector: 'tells', value: null,
  note: '', span: span(s, e),
})

const segment = (s: number, e: number, signals: Signal[]): Segment => ({
  span: span(s, e), signals, lean: 0.5, strength: 0.4, label: 'leans-machine',
})

const report = (segments: Segment[]): Report => ({
  text_sha256: 'x', n_chars: 100, document: segment(0, 100, []), segments,
  detectors: ['tells'], segmenter: 'paragraph', schema_version: '1',
  calibration: 'uncalibrated', meta: {},
})

/** Offset -> ProseMirror position, as the real editor's single wrapper node gives. */
const toPos = (offset: number) => offset + 1

/**
 * A stand-in for `tr.mapping.map`, modelling one insertion of `length` at `at`.
 * Positions strictly after `at` always shift. A position exactly *at* `at` shifts only
 * when the bias says it should end up after the inserted text.
 */
const insertion =
  (at: number, length: number) =>
  (pos: number, bias: number): number => {
    if (pos > at) return pos + length
    if (pos === at) return bias > 0 ? pos + length : pos
    return pos
  }

function scored(): State {
  return track(
    report([
      segment(0, 50, [signal('a', 0, 5), signal('b', 20, 25)]),
      segment(51, 100, [signal('c', 60, 65)]),
    ]),
    'x'.repeat(100),
    toPos,
  )
}

describe('a fresh report', () => {
  it('starts with nothing unverified', () => {
    const state = scored()
    expect(state.signals).toHaveLength(3)
    expect(state.signals.every((s) => !s.unverified)).toBe(true)
    expect(isStale(state)).toBe(false)
  })

  it('anchors every finding at its own offsets', () => {
    const state = scored()
    expect(state.signals.map((s) => [s.from, s.to])).toEqual([
      [1, 6], [21, 26], [61, 66],
    ])
  })
})

describe('an edit', () => {
  it('invalidates only the segment it touched', () => {
    // Insert inside the first segment, away from any finding.
    const edited = applyEdit(scored(), 'new', [[30, 33]], insertion(30, 3))
    const byName = Object.fromEntries(edited.signals.map((s) => [s.signal.name, s]))
    // Both findings in segment 0 go unverified, because the segment's own lean and
    // strength are computed per unit of text and the segment just got longer.
    expect(byName.a!.unverified).toBe(true)
    expect(byName.b!.unverified).toBe(true)
    // Segment 1 was not touched, so its finding still describes the text it is on.
    expect(byName.c!.unverified).toBe(false)
  })

  it('always invalidates the document verdict', () => {
    const edited = applyEdit(scored(), 'new', [[30, 33]], insertion(30, 3))
    expect(edited.documentUnverified).toBe(true)
    expect(isStale(edited)).toBe(true)
  })

  it('moves downstream findings by exactly the inserted length', () => {
    const edited = applyEdit(scored(), 'new', [[1, 11]], insertion(1, 10))
    const byName = Object.fromEntries(edited.signals.map((s) => [s.signal.name, s]))
    expect([byName.b!.from, byName.b!.to]).toEqual([31, 36])
    expect([byName.c!.from, byName.c!.to]).toEqual([71, 76])
  })

  it('never lets a finding swallow text inserted at its boundary', () => {
    // THE REGRESSION. With the biases the wrong way round, inserting at the very
    // start of the document made the first finding grow leftward to cover the new
    // text -- so a finding about five characters claimed fifteen it had never seen.
    // A browser caught this; this test is so a browser never has to again.
    const atStart = applyEdit(scored(), 'new', [[1, 11]], insertion(1, 10))
    const a = atStart.signals.find((s) => s.signal.name === 'a')!
    expect(a.to - a.from).toBe(5)
    expect(a.from).toBe(11)

    // ...and the same at the right-hand boundary.
    const atEnd = applyEdit(scored(), 'new', [[6, 16]], insertion(6, 10))
    const a2 = atEnd.signals.find((s) => s.signal.name === 'a')!
    expect(a2.to - a2.from).toBe(5)
    expect([a2.from, a2.to]).toEqual([1, 6])
  })

  it('marks a boundary-touching finding unverified even though it did not move', () => {
    // It keeps its characters, but the text immediately beside it changed, and the
    // segment score that produced its weight was computed without that text.
    const edited = applyEdit(scored(), 'new', [[6, 16]], insertion(6, 10))
    expect(edited.signals.find((s) => s.signal.name === 'a')!.unverified).toBe(true)
  })

  it('is cumulative: a second edit cannot un-invalidate the first', () => {
    const once = applyEdit(scored(), 'a', [[1, 4]], insertion(1, 3))
    const twice = applyEdit(once, 'b', [[80, 83]], insertion(80, 3))
    expect(twice.signals.find((s) => s.signal.name === 'a')!.unverified).toBe(true)
  })

  it('reports when nothing on screen describes the current text', () => {
    const state = scored()
    expect(allUnverified(state)).toBe(false)
    const everywhere = applyEdit(state, 'x', [[0, 200]], (p) => p)
    expect(allUnverified(everywhere)).toBe(true)
  })
})

describe('re-scoring', () => {
  it('replaces everything rather than reconciling with the stale findings', () => {
    // The whole point of the policy: a re-score is computed against the current text,
    // so its offsets are correct by construction and nothing is carried over.
    const stale = applyEdit(scored(), 'x', [[0, 200]], (p) => p)
    expect(isStale(stale)).toBe(true)
    const fresh = track(report([segment(0, 30, [signal('z', 3, 8)])]), 'y'.repeat(30), toPos)
    expect(isStale(fresh)).toBe(false)
    expect(fresh.signals.map((s) => s.signal.name)).toEqual(['z'])
    expect(fresh.documentUnverified).toBe(false)
  })
})

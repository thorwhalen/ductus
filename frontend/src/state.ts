/**
 * The one store, and the invalidation policy — which is the correctness rule of this
 * whole app.
 *
 * ## The rule: invalidate, never silently re-anchor
 *
 * When the text changes, a finding computed against the *old* text must stop claiming
 * to describe the new text. Keeping its position correct is plumbing and we do it
 * (ProseMirror's `Mapping`, see editor.ts). Keeping its *score* attached is a lie: that
 * number was never computed for the characters it now points at.
 *
 * So an edit does not delete findings and does not re-score them. It marks the affected
 * ones **unverified**, and they render dimmed until a re-score replaces them with
 * findings computed against the text as it now stands.
 *
 * ## What counts as "affected"
 *
 * Two levels, because the scores are computed at two levels:
 *
 * - A **finding** is affected when the edit touched its own characters, *or* touched
 *   anywhere in the segment it belongs to. The second half matters and is easy to miss:
 *   a segment's `lean` and `strength` come from `density_aggregate`, which divides the
 *   evidence by how much text produced it. Adding a sentence to a paragraph changes
 *   what every finding in that paragraph is worth, without touching any of them.
 * - The **document verdict** is affected by *any* edit at all, for the same reason one
 *   level up.
 *
 * ## Why this is not zustand
 *
 * One screen, one state object, one subscriber. The part of the house convention that
 * carries its weight here is "derived values are selectors, never duplicated state" —
 * and it is kept: nothing below is stored twice, and everything derivable is derived at
 * render time. See `misc/docs/frontend-stack-decision.md`.
 */

import type { Report, Segment, Signal } from './generated/report'

/** A finding, plus where it currently sits and whether it still describes the text. */
export interface TrackedSignal {
  /** Stable within one score run; used as a DOM id so hover can link list <-> text. */
  id: string
  signal: Signal
  /** ProseMirror positions, kept exact through every edit. */
  from: number
  to: number
  /** Index of the segment this finding was found in. */
  segment: number
  /** True once an edit has touched the text this finding's score was computed from. */
  unverified: boolean
}

/** A scored unit of text, tracked the same way. */
export interface TrackedSegment {
  index: number
  segment: Segment
  from: number
  to: number
  unverified: boolean
}

export type Status = 'empty' | 'scoring' | 'scored' | 'error'

export interface State {
  status: Status
  /** The last report received, or null. Never mutated; replaced wholesale. */
  report: Report | null
  /** The exact text the report was computed against. Kept for the staleness check. */
  scoredText: string | null
  /** The text in the editor right now. */
  text: string
  signals: TrackedSignal[]
  segments: TrackedSegment[]
  /** True once any edit has landed since the last score. Invalidates the document verdict. */
  documentUnverified: boolean
  error: string | null
  /** Which finding the pointer or keyboard is on, for the two-way highlight. */
  focused: string | null
}

export const initialState: State = {
  status: 'empty',
  report: null,
  scoredText: null,
  text: '',
  signals: [],
  segments: [],
  documentUnverified: false,
  error: null,
  focused: null,
}

/** True when there are findings, but none of them still describes the current text. */
export function allUnverified(state: State): boolean {
  return state.signals.length > 0 && state.signals.every((s) => s.unverified)
}

/** True when anything at all is stale: the verdict, or any finding. */
export function isStale(state: State): boolean {
  return state.documentUnverified || state.signals.some((s) => s.unverified)
}

/**
 * Build the tracked view of a fresh report.
 *
 * Offsets are correct by construction here: the report was just computed against
 * exactly this text, so there is no anchoring problem at this instant. Everything
 * afterwards is a matter of keeping those positions correct, which `Mapping` does
 * exactly. The redundant selectors (`quote`/`prefix`/`suffix`) that every `Span`
 * carries are for re-anchoring across a *reload*, which this app does not do — see
 * the decision doc.
 */
export function track(report: Report, text: string, toPos: (offset: number) => number): State {
  const segments: TrackedSegment[] = report.segments.map((segment, index) => ({
    index,
    segment,
    from: toPos(segment.span.start),
    to: toPos(segment.span.end),
    unverified: false,
  }))

  const signals: TrackedSignal[] = []
  report.segments.forEach((segment, index) => {
    segment.signals.forEach((signal, j) => {
      // A signal without a span is real evidence about the segment as a whole (a rate,
      // a ratio) rather than about a phrase. It belongs in the list but has nothing to
      // highlight, so it is anchored to its segment and rendered without a mark.
      const span = signal.span ?? segment.span
      signals.push({
        id: `${index}_${j}`,
        signal,
        from: toPos(span.start),
        to: toPos(span.end),
        segment: index,
        unverified: false,
      })
    })
  })

  return {
    status: 'scored',
    report,
    scoredText: text,
    text,
    signals,
    segments,
    documentUnverified: false,
    error: null,
    focused: null,
  }
}

const touches = (from: number, to: number, ranges: Array<[number, number]>): boolean =>
  // `<=` on both sides on purpose: an insertion exactly at a boundary is a change to
  // the text this finding is about, and treating it as untouched would leave a score
  // attached to characters that are no longer the ones it was computed from.
  ranges.some(([start, end]) => start <= to && end >= from)

/**
 * Which way a boundary leans when text is inserted exactly on it.
 *
 * ProseMirror's `bias` answers "does this position end up before or after content
 * inserted right here". For an annotation the answer is **outside, at both ends**: the
 * newly typed characters were never part of the quoted evidence, so the highlight must
 * not swallow them.
 *
 * That means `from` leans right (+1, ending up after the insertion) and `to` leans left
 * (-1, ending up before it) — the opposite of the intuitive reading, and the opposite of
 * what this code did first. A browser caught it: typing at the very start of the
 * document made the first highlight grow leftward to cover the new sentence, so a
 * finding about "Great question" claimed 74 characters it had never seen.
 */
const FROM_BIAS = 1
const TO_BIAS = -1

/**
 * Apply an edit: move every tracked position, then mark what the edit invalidated.
 *
 * `mapPos` is ProseMirror's `tr.mapping.map`, passed in rather than imported so this
 * module stays testable without an editor and so the policy reads independently of
 * the plumbing.
 */
export function applyEdit(
  state: State,
  text: string,
  ranges: Array<[number, number]>,
  mapPos: (pos: number, bias: number) => number,
): State {
  const segments = state.segments.map((s) => {
    const from = mapPos(s.from, FROM_BIAS)
    const to = mapPos(s.to, TO_BIAS)
    return { ...s, from, to, unverified: s.unverified || touches(from, to, ranges) }
  })

  const dirtySegments = new Set(segments.filter((s) => s.unverified).map((s) => s.index))

  const signals = state.signals.map((s) => {
    const from = mapPos(s.from, FROM_BIAS)
    const to = mapPos(s.to, TO_BIAS)
    return {
      ...s,
      from,
      to,
      unverified: s.unverified || dirtySegments.has(s.segment) || touches(from, to, ranges),
    }
  })

  return { ...state, text, segments, signals, documentUnverified: true }
}

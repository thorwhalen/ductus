/**
 * Turning findings into highlights, on two independent visual channels.
 *
 * The rule, which `ductus/render.py` already follows and this matches so the HTML
 * report and the UI cannot disagree about what a colour means:
 *
 * 1. **Hue encodes score, and only score.** One ramp for machine-leaning, one for
 *    human-leaning, lightness re-clamped per theme. Never overloaded to also mean
 *    "how many findings overlap here".
 * 2. **Overlap is structural, in a separate lane.** Two translucent fills stacked on
 *    top of each other blend into an unreadable third colour, and the reader cannot
 *    tell whether they are seeing one strong finding or two weak ones. So only the
 *    non-overlapping findings are painted onto the text, and every finding also gets a
 *    bar in a lane beneath — that lane is where "how many, and how strong" is legible.
 *
 * Human-leaning findings are painted exactly as prominently as machine-leaning ones.
 * A tool that shows accusations in colour and exonerations in grey is an accusation
 * machine whatever its documentation says.
 */

import { Decoration } from 'prosemirror-view'

import type { TrackedSignal } from './state'

/**
 * Background and underline colour for one finding.
 *
 * The weight is clamped to 0.10..0.60 and mapped onto the ramp, matching `_shade` in
 * `ductus/render.py`. `color-mix` in OKLab keeps the steps perceptually even, which a
 * plain alpha fade does not.
 */
export function shade(direction: string, weight: number): { fill: string; line: string } {
  const t = (Math.min(Math.max(weight, 0.1), 0.6) / 0.6) * 100
  if (direction === 'neutral') return { fill: 'transparent', line: 'var(--n1)' }
  const [low, high] = direction === 'machine' ? ['--m0', '--m1'] : ['--h0', '--h1']
  return {
    fill: `color-mix(in oklab, var(${high}) ${t.toFixed(0)}%, var(${low}))`,
    line: `var(${high})`,
  }
}

/**
 * Pick the findings that can be painted on the text without overlapping.
 *
 * Greedy, left to right, strongest first at any given start — the same rule as
 * `_placed` in `ductus/render.py`. Whatever loses is not hidden: it is in the lane and
 * in the findings list, both of which show everything.
 */
export function placeable(signals: TrackedSignal[]): TrackedSignal[] {
  const candidates = [...signals]
    .filter((s) => s.to > s.from)
    .sort((a, b) => a.from - b.from || b.signal.weight - a.signal.weight)
  const out: TrackedSignal[] = []
  let cursor = -1
  for (const s of candidates) {
    if (s.from >= cursor) {
      out.push(s)
      cursor = s.to
    }
  }
  return out
}

/**
 * The highlights for the current findings.
 *
 * An unverified finding keeps its position — that is exact — and loses its colour,
 * falling back to a hatched outline. The reader should be able to see *that* something
 * was found here and *that* the claim no longer applies, without being told a stale
 * score as though it were current.
 */
export function decorationsFor(signals: TrackedSignal[], focused: string | null): Decoration[] {
  return placeable(signals).map((s) => {
    const { fill, line } = shade(s.signal.direction, s.signal.weight)
    const classes = ['finding', `dir-${s.signal.direction}`]
    if (s.unverified) classes.push('unverified')
    if (s.id === focused) classes.push('focused')
    return Decoration.inline(s.from, s.to, {
      class: classes.join(' '),
      style: s.unverified ? '' : `--fill:${fill};--line:${line}`,
      'data-finding': s.id,
      // The reason is in the list beside the text; the title is the fallback for a
      // reader who is hovering rather than reading the list.
      title: `${s.signal.name} (${s.signal.direction}) — ${s.signal.note}`,
    })
  })
}

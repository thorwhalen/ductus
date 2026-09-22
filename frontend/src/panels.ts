/**
 * The chrome: the verdict, the findings list, and the limits.
 *
 * This file is where the honesty requirement is either met or quietly dropped, so the
 * reasoning is written next to the code rather than in a document nobody opens.
 *
 * **An interface makes a verdict feel authoritative in a way a text report does not.**
 * The colour arrives before the caveat, and the caveat is below the fold. The shipped
 * HTML report can put its limits in a footer; a screen cannot. So:
 *
 * - The measured false-positive rate sits *beside* the verdict, and is stated loudest
 *   in the one case where the verdict is a claim about a person — `leans-machine`.
 * - It is a natural frequency ("about one in sixteen"), not "6.0%": the no-percentage
 *   rule is load-bearing next to a verdict, and frequencies are read more accurately
 *   than rates.
 * - The findings list is the main column and the verdict is small, so the reader is
 *   pulled toward *what it found* rather than *what colour it is*.
 * - The bias direction is on screen, because the person most likely to be misled here
 *   is the one whose careful prose has just been lit up.
 * - The empty result says it is a weak result, not a clean bill.
 *
 * All of those numbers come from `misc/docs/reducing-false-accusations.md` and are the
 * measured ones. None of them is a probability that anyone used a model, and nothing
 * here can be inverted into one.
 */

import type { Report } from './generated/report'
import type { State, TrackedSignal } from './state'
import { allUnverified, isStale } from './state'

const el = <K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  ...children: Array<Node | string>
): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v)
  for (const child of children) node.append(child)
  return node
}

/** How a label reads in a sentence, in words a reader can act on. */
const LABEL_TEXT: Record<string, string> = {
  'leans-machine': 'This text carries more machine-leaning signals than human-leaning ones.',
  'leans-human': 'This text carries more human-leaning signals than machine-leaning ones.',
  'mixed-signals': 'This text carries signals pointing both ways.',
  uncertain: 'The evidence here is too thin to lean either way.',
  'no-evidence': 'None of the deterministic checks matched anything in this text.',
}

/**
 * The lean bar: a position between "human" and "machine", with no number on it that
 * could be read as a likelihood. The ends are labelled with what they mean, and the
 * strength is shown separately because a lean of +1.0 from one weak signal is not the
 * same claim as +1.0 from six.
 */
function leanBar(lean: number, strength: number): HTMLElement {
  const bar = el('div', { class: 'lean-bar', role: 'img',
    'aria-label': `lean ${lean.toFixed(2)} on a scale from -1 human-leaning to +1 machine-leaning, evidence strength ${strength.toFixed(2)}` })
  bar.append(
    el('span', { class: 'lean-end' }, 'human-leaning'),
    el('div', { class: 'lean-track' },
      el('i', { class: 'lean-mark', style: `left:${((lean + 1) / 2) * 100}%` })),
    el('span', { class: 'lean-end' }, 'machine-leaning'),
  )
  return bar
}

/**
 * The verdict, and — inseparably — what it is worth.
 *
 * The false-positive line is not a dismissible notice and not a footnote. It is part of
 * the verdict block, because it is part of the verdict.
 */
export function verdictPanel(state: State): HTMLElement {
  const panel = el('section', { class: 'verdict', 'aria-live': 'polite' })

  if (state.status === 'scoring') {
    panel.append(el('p', { class: 'muted' }, 'Reading…'))
    return panel
  }
  if (state.status === 'error') {
    panel.append(
      el('p', { class: 'error' }, state.error ?? 'Something went wrong.'),
    )
    return panel
  }
  if (!state.report) {
    panel.append(
      el('p', { class: 'muted' },
        'Paste or type some text, then read it. Nothing is uploaded until you do, ' +
        'and nothing is stored afterwards.'),
    )
    return panel
  }

  const doc = state.report.document
  const stale = state.documentUnverified

  panel.append(
    el('div', { class: `verdict-head label-${doc.label}${stale ? ' unverified' : ''}` },
      el('span', { class: 'verdict-label' }, doc.label.replace(/-/g, ' ')),
      el('span', { class: 'verdict-meta' },
        `${state.report.segments.length} ${state.report.segmenter}(s), ` +
        `${state.report.n_chars} characters`)),
    el('p', { class: 'verdict-sentence' }, LABEL_TEXT[doc.label] ?? doc.label),
    leanBar(doc.lean, doc.strength),
  )

  if (stale) {
    panel.append(
      el('p', { class: 'stale-note' },
        'You have edited the text since this was computed, so it describes the ' +
        'earlier version. Read it again to get a verdict about what is on screen now.'),
    )
  }

  // The part that a UI most easily gets wrong: saying, at the moment of the
  // accusation, how often this exact label is wrong.
  if (doc.label === 'leans-machine') {
    panel.append(
      el('div', { class: 'honesty loud' },
        el('p', {},
          el('strong', {}, 'About one human-written document in sixteen gets this ' +
            'same label from this tool.'),
          ' Measured on 350 texts people wrote. If this is your own writing, that is ' +
          'the most likely explanation of what you are looking at.'),
        el('p', {},
          'The bias runs toward ', el('em', {}, 'formal, fluent'), ' prose — not ' +
          'toward simple prose, and not toward non-native writers. In the measured ' +
          'corpus the native-speaker control was the most-accused group. A careful ' +
          'essayist is the likeliest person to be wronged by this page.'),
        el('p', {},
          'A flagged ', el('em', {}, 'sentence'), ' below is much better evidence ' +
          'than this document-level label. Read the findings, not the colour.')),
    )
  } else if (doc.label === 'no-evidence' || state.signals.length === 0) {
    panel.append(
      el('div', { class: 'honesty' },
        el('p', {},
          el('strong', {}, 'Finding nothing is a weak result, not a clean bill.'),
          ' These checks have high precision and low recall: they catch a small ' +
          'number of specific habits, and miss most machine-written text. An empty ' +
          'result means these particular checks did not match — nothing more.')),
    )
  } else {
    // Every other verdict still gets a note. A reader who sees orange on the page is
    // owed the error rate whether or not the label came out as an accusation, and a
    // limits box that only appears when the tool accuses you teaches the reader that
    // its silence means confidence.
    panel.append(
      el('div', { class: 'honesty' },
        el('p', {},
          'These are weights on quoted phrases, not a probability that anyone used a ' +
          'model. About one human-written document in sixteen is called ' +
          'machine-leaning by this tool; the bias runs toward formal, fluent prose. ',
          el('strong', {}, 'Read the findings, not the colour.'))),
    )
  }

  return panel
}

/** One finding: its quote, its direction, its weight, and why it fired. */
function findingRow(tracked: TrackedSignal, focused: boolean): HTMLElement {
  const { signal } = tracked
  const row = el('li', {
    class: [
      'finding-row',
      `dir-${signal.direction}`,
      tracked.unverified ? 'unverified' : '',
      focused ? 'focused' : '',
    ].filter(Boolean).join(' '),
    'data-finding': tracked.id,
    tabindex: '0',
  })

  row.append(
    el('div', { class: 'finding-head' },
      el('span', { class: 'finding-name' }, signal.name),
      el('span', { class: 'finding-dir' },
        signal.direction === 'machine' ? 'machine-leaning'
          : signal.direction === 'human' ? 'human-leaning' : 'neutral'),
      el('span', { class: 'finding-weight', title: 'weight, not a probability' },
        `weight ${signal.weight.toFixed(2)}`)),
  )
  if (signal.span?.quote) {
    row.append(el('blockquote', { class: 'finding-quote' }, signal.span.quote))
  }
  row.append(el('p', { class: 'finding-note' }, signal.note))
  if (tracked.unverified) {
    row.append(
      el('p', { class: 'finding-stale' },
        'Unverified: the text this was computed from has changed.'),
    )
  }
  return row
}

/**
 * The findings, which are the actual content of this page.
 *
 * Human-leaning findings come first when they exist, and are not visually demoted.
 * They are frequently the most decisive evidence in a file, and a reader scanning for
 * "what did it find" should meet an exoneration as readily as an accusation.
 */
export function findingsPanel(
  state: State,
  onFocus: (id: string | null) => void,
): HTMLElement {
  const panel = el('section', { class: 'findings' })
  // Nothing to say yet: return an empty fragment rather than an empty bordered box,
  // which reads as a panel that failed to load.
  if (!state.report) return panel

  const heading = el('h2', {}, `Findings (${state.signals.length})`)
  panel.append(heading)

  if (state.signals.length === 0) {
    panel.append(
      el('p', { class: 'muted' },
        'Nothing matched. See the note above about what that does and does not mean.'),
    )
    return panel
  }

  if (allUnverified(state)) {
    panel.append(
      el('p', { class: 'stale-note' },
        'Every finding below describes text you have since edited.'),
    )
  }

  const ordered = [...state.signals].sort((a, b) => {
    const rank = (d: string) => (d === 'human' ? 0 : d === 'machine' ? 1 : 2)
    return rank(a.signal.direction) - rank(b.signal.direction) ||
      b.signal.weight - a.signal.weight
  })

  const list = el('ul', { class: 'finding-list' })
  for (const tracked of ordered) {
    const row = findingRow(tracked, tracked.id === state.focused)
    row.addEventListener('mouseenter', () => onFocus(tracked.id))
    row.addEventListener('mouseleave', () => onFocus(null))
    row.addEventListener('focus', () => onFocus(tracked.id))
    row.addEventListener('blur', () => onFocus(null))
    list.append(row)
  }
  panel.append(list)
  return panel
}

/**
 * The standing limits: true of every result, shown whether or not anything was found.
 *
 * Kept short enough to actually be read. The longer argument is in the repository and
 * linked, but a reader who reads only this box should still come away understanding
 * what the tool did and did not just claim.
 */
export function limitsPanel(report: Report | null): HTMLElement {
  const panel = el('aside', { class: 'limits' })
  panel.append(
    el('h2', {}, 'What this is, and is not'),
    el('ul', {},
      el('li', {},
        el('strong', {}, 'Evidence, not a verdict about a person.'),
        ' Every number here is a weight on a quoted piece of text. None of them is a ' +
        'probability that anyone used a model, and none of them can be turned into one.'),
      el('li', {},
        el('strong', {}, 'Measured error rate: about one human-written document in ' +
          'sixteen is called machine-leaning.'),
        ' Per sentence it is far lower, which is why a flagged sentence is much ' +
        'better evidence than a flagged document.'),
      el('li', {},
        el('strong', {}, 'Biased toward formal, fluent writing.'),
        ' The checks fire on tricolons, "not X but Y", and discourse openers — things ' +
        'a model emits and a well-taught essayist also writes.'),
      el('li', {},
        el('strong', {}, 'Editing confounds it.'),
        ' Heavily-edited human writing and model-assisted writing produce overlapping ' +
        'signatures. This cannot tell them apart, and neither can anything else.'),
      el('li', {},
        el('strong', {}, 'Do not use this to accuse someone.')),
    ),
  )
  if (report) {
    panel.append(
      el('p', { class: 'provenance' },
        `detectors: ${report.detectors.join(', ')} · segmenter: ${report.segmenter} · ` +
        `calibration: ${report.calibration} · sha256 ${report.text_sha256.slice(0, 16)}`),
    )
  }
  return panel
}

/** The banner across the top of the editor when anything on screen is out of date. */
export function staleBanner(state: State): HTMLElement | null {
  if (!isStale(state) || state.status === 'scoring') return null
  return el('div', { class: 'stale-banner', role: 'status' },
    'Edited since reading — dimmed findings describe the earlier text.')
}

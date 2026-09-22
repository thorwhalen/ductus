/**
 * The editor: a ProseMirror instance that preserves every character exactly, and
 * keeps the position of each finding correct while you type.
 *
 * ## Why ProseMirror and not a `<textarea>`
 *
 * A `<textarea>` cannot draw anything inside itself. To highlight a phrase you need
 * real DOM elements around real characters, and to keep those elements attached while
 * the text changes underneath them you need to know, exactly, where every character
 * moved. ProseMirror is the one editor whose model gives you that for free: every
 * edit is a `Transaction` carrying a `Mapping`, and `mapping.map(pos)` tells you where
 * position `pos` ended up. No guessing, no re-searching the text.
 *
 * ## The schema, which is the important decision here
 *
 * A normal rich-text editor tidies text as you type: it turns `'` into `'`, trims
 * trailing spaces, and collapses lone newlines into paragraph breaks. **Every one of
 * those is evidence `ductus` reads.** `mixed-apostrophes` (weight 0.35, human-leaning),
 * `trailing-whitespace` (0.25, human) and `mid-sentence-newline` are among the
 * strongest signals that a person, not a model, wrote something. A tidying editor would
 * delete the evidence that exonerates people, invisibly.
 *
 * So the schema here is one block node that holds text and nothing else, with
 * whitespace preserved. That has a second benefit worth as much: the offset arithmetic
 * becomes nearly trivial. ProseMirror counts positions that include node boundaries,
 * and with exactly one wrapper node a UTF-16 index `i` into the text is position
 * `i + 1`. One conversion remains, and it is not about nodes: `ductus` is Python and
 * reports offsets in *code points*, which differ from UTF-16 indices after any emoji
 * or other astral character. That conversion lives in `offsets.ts` (`positionsIn`),
 * built from the scored text (#11).
 */

import { baseKeymap, newlineInCode } from 'prosemirror-commands'
import { history, redo, undo } from 'prosemirror-history'
import { keymap } from 'prosemirror-keymap'
import { Schema } from 'prosemirror-model'
import { EditorState, Transaction } from 'prosemirror-state'
import { Decoration, DecorationSet, EditorView } from 'prosemirror-view'

/**
 * `doc > body > text`. `code: true` is what tells ProseMirror to preserve whitespace
 * and to refuse marks — there is no bold here, only characters.
 */
export const schema = new Schema({
  nodes: {
    doc: { content: 'body' },
    body: {
      content: 'text*',
      code: true,
      parseDOM: [{ tag: 'div.ductus-body', preserveWhitespace: 'full' }],
      toDOM: () => ['div', { class: 'ductus-body' }, 0],
    },
    text: { group: 'inline' },
  },
})

/** The document's text, exactly as the user has it and exactly as `ductus` will see it. */
export function textOf(state: EditorState): string {
  return state.doc.textBetween(0, state.doc.content.size, '\n', '\n')
}

function docFromText(text: string) {
  const body = schema.nodes.body!
  return schema.nodes.doc!.create(null, text ? body.create(null, schema.text(text)) : body.create())
}

/**
 * The ranges a transaction changed, expressed in the *new* document's coordinates.
 *
 * Used to decide which findings an edit invalidated. A transaction can hold several
 * steps, and each step's `StepMap` reports its changed range in the coordinates that
 * existed just after that step — so each range is pushed through the remaining steps to
 * land in the final document. This is the standard ProseMirror idiom for the question
 * "what did this transaction touch".
 */
export function changedRanges(tr: Transaction): Array<[number, number]> {
  const ranges: Array<[number, number]> = []
  tr.mapping.maps.forEach((stepMap, index) => {
    const remaining = tr.mapping.slice(index + 1)
    stepMap.forEach((_oldStart, _oldEnd, newStart, newEnd) => {
      ranges.push([remaining.map(newStart, -1), remaining.map(newEnd, 1)])
    })
  })
  return ranges
}

/** What the editor reports upward after every change. */
export interface EditorEvent {
  /** The document's full text, right now. */
  text: string
  /** True when this transaction changed the text (as opposed to moving the cursor). */
  docChanged: boolean
  /** The transaction, so the caller can map its own positions through it. */
  tr: Transaction
}

export interface EditorHandle {
  view: EditorView
  /**
   * Replace the whole document. Used when a sample is loaded, not while typing.
   *
   * Deliberately does NOT report an edit: an edit maps existing findings onto changed
   * text, and there is no correspondence to map here. The caller resets its state.
   */
  setText(text: string): void
  /** Redraw the highlights. The caller owns the spans; the editor only paints them. */
  setDecorations(decorations: Decoration[]): void
  focus(): void
}

/**
 * Mount the editor into `parent`.
 *
 * The decorations live in a plugin-free side channel — a variable this module holds,
 * handed to `props.decorations`. They are deliberately **not** part of the document:
 * a finding is something said *about* the text, not part of it, and putting it in the
 * document would mean an edit could corrupt it and a copy-paste would carry it.
 */
export function mountEditor(
  parent: HTMLElement,
  onEvent: (event: EditorEvent) => void,
): EditorHandle {
  let decorations = DecorationSet.empty

  const view = new EditorView(parent, {
    state: EditorState.create({
      doc: docFromText(''),
      plugins: [
        history(),
        // Enter must insert a literal newline rather than starting a new block: the
        // whole point of this schema is that a newline is a character like any other.
        keymap({ Enter: newlineInCode, 'Mod-z': undo, 'Mod-y': redo, 'Shift-Mod-z': redo }),
        keymap(baseKeymap),
      ],
    }),
    // `decorations` is a prop on the view itself, re-read on every redraw. This is the
    // side channel: the findings are drawn over the document without being in it.
    decorations: () => decorations,
    /*
     * Paste the plain text, never the HTML.
     *
     * This app is used by pasting from a word processor, a browser or a chat window.
     * Letting ProseMirror parse the clipboard's `text/html` would re-derive the text
     * from someone else's markup, and the characters that arrive would be that
     * renderer's idea of the text rather than the author's. The whole premise here is
     * that the exact characters are the evidence, so we take the exact characters.
     */
    handlePaste(view, event) {
      const text = event.clipboardData?.getData('text/plain')
      if (text == null) return false
      view.dispatch(view.state.tr.insertText(text).scrollIntoView())
      return true
    },
    dispatchTransaction(tr) {
      // Keep the highlights pinned to their characters through this edit. This is the
      // exact-position half of the design; deciding which of them are now *stale* is
      // the caller's job, and a separate question — see state.ts.
      decorations = decorations.map(tr.mapping, tr.doc)
      view.updateState(view.state.apply(tr))
      onEvent({ text: textOf(view.state), docChanged: tr.docChanged, tr })
    },
  })

  return {
    view,
    setText(text: string) {
      const state = EditorState.create({ doc: docFromText(text), plugins: view.state.plugins })
      decorations = DecorationSet.empty
      view.updateState(state)
    },
    setDecorations(list: Decoration[]) {
      decorations = DecorationSet.create(view.state.doc, list)
      // `setMeta` on an empty transaction is the documented way to ask for a redraw
      // without changing the document.
      view.dispatch(view.state.tr.setMeta('ductus-redraw', true))
    },
    focus() {
      view.focus()
    },
  }
}

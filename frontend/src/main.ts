/**
 * Wiring: the editor, the store, the panels and the one network call.
 *
 * Read this file top to bottom and you have the whole app. There are three actions —
 * read, edit, read again — and the interesting one is the middle one, which does *not*
 * call the server and does *not* change any score.
 */

import './styles.css'

import { DuctusClient } from './generated/client'
import type { Report } from './generated/report'
import { decorationsFor } from './decorations'
import { changedRanges, mountEditor, toPos } from './editor'
import { findingsPanel, limitsPanel, staleBanner, verdictPanel } from './panels'
import { applyEdit, initialState, track, type State } from './state'
import { ACCEPT, openTextFile, type FileLike } from './upload'

// Empty base URL: every request is relative, which is correct both when uvicorn serves
// the built assets itself and when Vite proxies them in development.
const api = new DuctusClient('')

const SAMPLE = `Great question! Let's delve into this rich tapestry.

In today's fast-paced world, it's not just about writing well — it's about
understanding your audience, respecting their time, and delivering value. The key
is to leverage your unique voice while maintaining clarity, consistency, and impact.

Sent it Friday. Two sites, not five — the third one fell through when their
procurement person went on leave, so we're down to Harlow and the Dagenham unit.
i'll chase them monday.`

let state: State = initialState

const root = document.getElementById('app')!
const editorHost = document.getElementById('editor')!
const sidebar = document.getElementById('sidebar')!
const readButton = document.getElementById('read') as HTMLButtonElement
const sampleButton = document.getElementById('sample') as HTMLButtonElement
const openButton = document.getElementById('open') as HTMLButtonElement
const fileInput = document.getElementById('file') as HTMLInputElement
const bannerHost = document.getElementById('banner')!
const editorPane = document.getElementById('editor-pane')!

const editor = mountEditor(editorHost, (event) => {
  if (!event.docChanged) return
  // An edit never re-scores and never re-anchors a score. It moves positions (exact,
  // via the transaction's Mapping) and marks what it invalidated.
  state = applyEdit(state, event.text, changedRanges(event.tr), (pos, bias) =>
    event.tr.mapping.map(pos, bias),
  )
  render()
})

function setState(next: State) {
  state = next
  render()
}

function render() {
  readButton.disabled = state.status === 'scoring' || state.text.trim().length === 0
  readButton.textContent =
    state.status === 'scoring' ? 'Reading…' : state.report ? 'Read again' : 'Read this text'

  // Rebuilding the sidebar wholesale is fine at this size and removes a whole class of
  // "the DOM and the state disagree" bug. The editor is never rebuilt — ProseMirror
  // owns that subtree and rebuilding it would destroy the cursor.
  sidebar.replaceChildren(
    verdictPanel(state),
    // The findings panel has nothing to show before the first read; an empty bordered
    // box there reads as a panel that failed to load.
    ...(state.report ? [findingsPanel(state, focusFinding)] : []),
    limitsPanel(state.report),
  )

  // ProseMirror keeps a trailing <br> in an "empty" document, so `:empty` never
  // matches and a CSS-only placeholder would never appear. The state knows the truth.
  editorPane.dataset.empty = String(state.text.length === 0)

  const banner = staleBanner(state)
  bannerHost.replaceChildren(...(banner ? [banner] : []))
  root.dataset.status = state.status

  editor.setDecorations(decorationsFor(state.signals, state.focused))
}

function focusFinding(id: string | null) {
  if (state.focused === id) return
  state = { ...state, focused: id }
  render()
}

/** Hovering a highlight in the text lights up its row in the list, and vice versa. */
editorHost.addEventListener('mouseover', (event) => {
  const mark = (event.target as HTMLElement).closest('[data-finding]')
  focusFinding(mark ? mark.getAttribute('data-finding') : null)
})
editorHost.addEventListener('mouseleave', () => focusFinding(null))

async function read() {
  const text = state.text
  if (!text.trim()) return
  // `tw-frontend-ux` principle 1: switch to the loading state immediately, and do not
  // leave the previous result sitting there looking current. The findings stay visible
  // but the verdict panel becomes "Reading…", so nothing on screen claims to describe
  // text it has not seen.
  setState({ ...state, status: 'scoring', error: null })
  try {
    // `format: 'json'` returns the whole Report as a JSON string.
    const raw = await api.gauge(text, 'json')
    const report = JSON.parse(raw) as Report
    setState(track(report, text, toPos))
  } catch (error) {
    setState({
      ...state,
      status: 'error',
      error:
        error instanceof Error
          ? `${error.message}. Is the ductus server running? (\`ductus-http\`)`
          : String(error),
    })
  }
}

readButton.addEventListener('click', read)
/** Replace the whole text: the sample, or an opened file. */
function loadText(text: string) {
  editor.setText(text)
  // A wholesale replacement is not an edit: there is no correspondence between the old
  // findings and the new text, so there is nothing to map and nothing to mark stale.
  // Anything less than a full reset would leave findings pointing into a document they
  // were never computed against.
  setState({ ...initialState, text })
  editor.focus()
}

sampleButton.addEventListener('click', () => loadText(SAMPLE))

/**
 * Opening a file is a paste you did not have to copy: read in the browser, put in the
 * editor, sent nowhere until "Read". The byte-level rules live in upload.ts.
 */
async function openFile(file: FileLike) {
  const opened = await openTextFile(file)
  if (opened.ok) loadText(opened.text)
  // A refused file leaves the current text alone; losing someone's edits because they
  // picked the wrong file would be the worse surprise.
  else setState({ ...state, status: 'error', error: opened.reason })
}

fileInput.accept = ACCEPT
openButton.addEventListener('click', () => fileInput.click())
fileInput.addEventListener('change', () => {
  const file = fileInput.files?.[0]
  // Reset so picking the same file again still fires `change`.
  fileInput.value = ''
  if (file) void openFile(file)
})

// Dropping a file on the editor opens it. Only files are intercepted: dragging text
// within or into the editor is ProseMirror's, and stays an ordinary edit.
const carriesFiles = (event: DragEvent) =>
  Array.from(event.dataTransfer?.types ?? []).includes('Files')
editorPane.addEventListener('dragover', (event) => {
  if (carriesFiles(event)) event.preventDefault()
})
editorPane.addEventListener(
  'drop',
  (event) => {
    if (!carriesFiles(event)) return
    event.preventDefault()
    event.stopPropagation()
    const file = event.dataTransfer?.files[0]
    if (file) void openFile(file)
  },
  { capture: true },
)

// Ctrl/Cmd-Enter reads, because that is what every editor-with-a-run-button does.
document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    event.preventDefault()
    void read()
  }
})

render()

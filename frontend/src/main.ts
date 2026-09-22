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

/**
 * A message about a file that could not be opened. Deliberately NOT `state.error`:
 * a refused file says nothing about the text or its reading, so it must not replace a
 * valid verdict, nor re-enable "Read" mid-request. Cleared by the next thing you do.
 */
let notice: string | null = null

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
  notice = null
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
  const scoring = state.status === 'scoring'
  readButton.disabled = scoring || state.text.trim().length === 0
  // Replacing the text mid-read would pair the old text's report with the new text.
  openButton.disabled = scoring
  sampleButton.disabled = scoring
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
  const noticeEl = notice
    ? Object.assign(document.createElement('div'), {
        className: 'notice-banner',
        role: 'status',
        textContent: notice,
      })
    : null
  bannerHost.replaceChildren(...[noticeEl, banner].filter((x): x is HTMLElement => x !== null))
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
  notice = null
  // `tw-frontend-ux` principle 1: switch to the loading state immediately, and do not
  // leave the previous result sitting there looking current. The findings stay visible
  // but the verdict panel becomes "Reading…", so nothing on screen claims to describe
  // text it has not seen.
  setState({ ...state, status: 'scoring', error: null })
  try {
    // `format: 'json'` returns the whole Report as a JSON string.
    const raw = await api.gauge(text, 'json')
    const report = JSON.parse(raw) as Report
    // Typing is still possible while a read is in flight. A report for text that is no
    // longer in the editor describes nothing on screen: drop it, keep what was there.
    if (state.text !== text) {
      setState({ ...state, status: state.report ? 'scored' : 'empty' })
      return
    }
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
/**
 * Replace the whole text: the sample, or an opened file. Replacing is not undoable
 * (a fresh editor state, see `setText`), so unsaved text is only replaced on a yes.
 */
function loadText(text: string): boolean {
  if (state.text.trim() && state.text !== text &&
      !window.confirm('Replace the text in the editor? This cannot be undone.')) {
    return false
  }
  notice = null
  editor.setText(text)
  // A wholesale replacement is not an edit: there is no correspondence between the old
  // findings and the new text, so there is nothing to map and nothing to mark stale.
  // Anything less than a full reset would leave findings pointing into a document they
  // were never computed against.
  setState({ ...initialState, text })
  editor.focus()
  return true
}

sampleButton.addEventListener('click', () => void loadText(SAMPLE))

/**
 * Opening a file is a paste you did not have to copy: read in the browser, put in the
 * editor, sent nowhere until "Read". The byte-level rules live in upload.ts.
 */
let lastOpen = 0
// A function, not an inline test: `state` changes across the `await` below, and an
// inline comparison would be narrowed by TypeScript as if it could not.
const isScoring = () => state.status === 'scoring'

async function openFile(file: FileLike) {
  if (isScoring()) return
  // Last *requested* wins, not last to finish reading: a big file picked first must
  // not overwrite a small one picked after it.
  const ticket = ++lastOpen
  const opened = await openTextFile(file)
  if (ticket !== lastOpen || isScoring()) return
  if (opened.ok) {
    loadText(opened.text)
    return
  }
  // A refused file leaves the text, the reading and the verdict exactly as they were.
  notice = opened.reason
  render()
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
// A file dropped anywhere else must not make the browser navigate to it, taking the
// unsaved text with it. The window-level handlers only prevent that default.
window.addEventListener('dragover', (event) => {
  if (carriesFiles(event)) event.preventDefault()
})
window.addEventListener('drop', (event) => {
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

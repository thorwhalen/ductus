/**
 * Opening a local file: turn its bytes into the exact text `ductus` would read.
 *
 * ## Where the file goes
 *
 * Nowhere. It is read in the browser and put in the editor, exactly as if it had been
 * pasted; nothing is sent until you press "Read", and then only the text, as with a
 * paste. Nothing is kept after the tab closes — persistence is a separate, deliberately
 * unmade decision (see the roadmap).
 *
 * ## The one rule: the same file reads the same here as at the command line
 *
 * `ductus gauge notes.txt` opens the file as UTF-8 text in Python, which does three
 * things a naive browser read would not:
 *
 * - **It refuses bytes that are not UTF-8** instead of quietly substituting `�`. A
 *   replacement character is a character `ductus` would score; silently inventing
 *   evidence is worse than saying the file could not be read.
 * - **It turns `\r\n` and lone `\r` into `\n`** (Python's universal newlines). Pasting
 *   does the same in every browser, so without this an opened file and the same text
 *   pasted would carry different offsets.
 * - **It keeps a byte-order mark** as the character U+FEFF, because Python's `utf-8`
 *   codec (unlike `utf-8-sig`) does. The browser's decoder strips it by default.
 *
 * Nothing else is touched — no trimming, no quote tidying — for the reason given at the
 * top of `editor.ts`: that tidying deletes the evidence that exonerates people.
 *
 * ## What is refused
 *
 * PDF, Word and anything else that is not text. Getting text out of a PDF is a
 * different problem — its line breaks, hyphenation and ligatures are artefacts of the
 * extractor, and `ductus` would score them as if a person had typed them. That needs
 * its own design, not a branch in this function.
 */

/** Extensions accepted as text, lower-case, with the dot. */
export const TEXT_EXTENSIONS: readonly string[] = ['.txt', '.md', '.markdown', '.text']

/** The `accept` attribute for the file picker, derived so it cannot drift. */
export const ACCEPT = [...TEXT_EXTENSIONS, 'text/plain', 'text/markdown'].join(',')

/**
 * Largest file opened, in bytes. Far above any single piece of writing — a novel is
 * about 1 MB — and low enough that an accidental pick of a log or a dataset is refused
 * with a reason rather than freezing the editor.
 */
export const MAX_BYTES = 2_000_000

export type Opened = { ok: true; text: string } | { ok: false; reason: string }

/** The subset of the DOM `File` this needs — lets tests pass a plain object. */
export interface FileLike {
  name: string
  size: number
  arrayBuffer(): Promise<ArrayBuffer>
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot <= 0 ? '' : name.slice(dot).toLowerCase()
}

/** Line endings as Python's universal-newlines text mode leaves them. */
export function universalNewlines(text: string): string {
  return text.replace(/\r\n?/g, '\n')
}

/** Why a file cannot be opened, or `null` if its name and size are acceptable. */
export function refusal(file: Pick<FileLike, 'name' | 'size'>): string | null {
  const ext = extensionOf(file.name)
  if (ext === '.pdf') {
    return `${file.name} is a PDF. Copy its text and paste it instead — text extracted from a PDF carries the extractor's line breaks and hyphenation, which would be read as the writer's.`
  }
  if (!TEXT_EXTENSIONS.includes(ext)) {
    return `${file.name} is not a text file. Open a ${TEXT_EXTENSIONS.join(', ')} file, or paste the text.`
  }
  if (file.size > MAX_BYTES) {
    const mb = (n: number) => (n / 1_000_000).toFixed(1)
    return `${file.name} is ${mb(file.size)} MB; the limit is ${mb(MAX_BYTES)} MB.`
  }
  return null
}

/** Decode bytes exactly as `open(path, encoding='utf-8').read()` would. */
export function decodeAsPython(bytes: ArrayBuffer): string {
  // fatal: refuse invalid UTF-8 (Python raises). ignoreBOM: keep U+FEFF (Python keeps it).
  const decoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true })
  return universalNewlines(decoder.decode(bytes))
}

/** Read a picked or dropped file into the text the editor should hold. */
export async function openTextFile(file: FileLike): Promise<Opened> {
  const refused = refusal(file)
  if (refused) return { ok: false, reason: refused }
  let bytes: ArrayBuffer
  try {
    bytes = await file.arrayBuffer()
  } catch (error) {
    return { ok: false, reason: `${file.name} could not be read: ${String(error)}` }
  }
  try {
    return { ok: true, text: decodeAsPython(bytes) }
  } catch {
    return {
      ok: false,
      reason: `${file.name} is not UTF-8 text. Save it as UTF-8, or paste the text.`,
    }
  }
}

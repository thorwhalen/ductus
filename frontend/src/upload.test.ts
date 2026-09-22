/**
 * Opening a file must yield the text `ductus gauge <file>` would read — no more, no less.
 */

import { describe, expect, it } from 'vitest'

import { ACCEPT, MAX_BYTES, openTextFile, refusal, TEXT_EXTENSIONS, type FileLike } from './upload'

const fileOf = (name: string, bytes: Uint8Array | string, size?: number): FileLike => {
  const data = typeof bytes === 'string' ? new TextEncoder().encode(bytes) : bytes
  return {
    name,
    size: size ?? data.byteLength,
    arrayBuffer: async () =>
      data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) as ArrayBuffer,
  }
}

describe('openTextFile', () => {
  it('returns the text of a UTF-8 file unchanged', async () => {
    const text = "it's  not tidied — ‘quotes’ stay,\ntrailing space stays \n"
    expect(await openTextFile(fileOf('a.txt', text))).toEqual({ ok: true, text })
  })

  it('turns \\r\\n and lone \\r into \\n, as Python text mode does', async () => {
    const opened = await openTextFile(fileOf('a.md', 'one\r\ntwo\rthree\n'))
    expect(opened).toEqual({ ok: true, text: 'one\ntwo\nthree\n' })
  })

  it('keeps a byte-order mark, as Python\'s utf-8 codec does', async () => {
    const bom = new Uint8Array([0xef, 0xbb, 0xbf, 0x68, 0x69])
    expect(await openTextFile(fileOf('a.txt', bom))).toEqual({ ok: true, text: '﻿hi' })
  })

  it('refuses bytes that are not UTF-8 rather than inventing replacement characters', async () => {
    const latin1 = new Uint8Array([0x63, 0x61, 0x66, 0xe9]) // "café" in Latin-1
    const opened = await openTextFile(fileOf('a.txt', latin1))
    expect(opened.ok).toBe(false)
    if (!opened.ok) expect(opened.reason).toMatch(/not UTF-8/)
  })

  it('refuses a PDF and says why pasting is the way', async () => {
    const opened = await openTextFile(fileOf('paper.pdf', '%PDF-1.7'))
    expect(opened.ok).toBe(false)
    if (!opened.ok) expect(opened.reason).toMatch(/PDF/)
  })

  it('does not read a refused file at all', async () => {
    let read = false
    const file: FileLike = {
      name: 'huge.txt',
      size: MAX_BYTES + 1,
      arrayBuffer: async () => {
        read = true
        return new ArrayBuffer(0)
      },
    }
    expect((await openTextFile(file)).ok).toBe(false)
    expect(read).toBe(false)
  })

  it('reports a read failure instead of throwing', async () => {
    const file: FileLike = {
      name: 'gone.txt',
      size: 3,
      arrayBuffer: async () => {
        throw new Error('NotReadableError')
      },
    }
    const opened = await openTextFile(file)
    expect(opened.ok).toBe(false)
  })
})

describe('refusal', () => {
  it('accepts every listed extension, in any case', () => {
    for (const ext of TEXT_EXTENSIONS) {
      expect(refusal({ name: `x${ext.toUpperCase()}`, size: 1 })).toBeNull()
    }
  })

  it('refuses a name with no extension, and a dotfile', () => {
    expect(refusal({ name: 'README', size: 1 })).not.toBeNull()
    expect(refusal({ name: '.txt', size: 1 })).not.toBeNull()
  })

  it('accepts exactly the limit and refuses one byte over', () => {
    expect(refusal({ name: 'a.txt', size: MAX_BYTES })).toBeNull()
    expect(refusal({ name: 'a.txt', size: MAX_BYTES + 1 })).not.toBeNull()
  })

  it('offers the picker every accepted extension', () => {
    for (const ext of TEXT_EXTENSIONS) expect(ACCEPT.split(',')).toContain(ext)
  })
})

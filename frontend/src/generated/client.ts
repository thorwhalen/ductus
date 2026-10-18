// Generated from this service's own OpenAPI by `ductus.http.export_client()`.
// Do not edit by hand: `python misc/generate_frontend_sources.py` rewrites it,
// and tests/test_generated_sources.py fails if this file and the Python disagree.

export interface GaugeParams {
  source: string;
  format?: string;
  segmenter?: string;
  detectors?: string | string[] | null;
  judgments?: string | string[] | null;
  k?: number;
  baseline?: string | Record<string, any> | null;
  out?: string | null;
  title?: string | null;
}

export interface BaselineParams {
  sources: string[];
  judgments_dir?: string | null;
  k?: number;
  format?: string;
  out?: string | null;
}

export interface DetectorsParams {

}

export interface SegmentersParams {

}

export interface TellsParams {
  tier?: string | null;
}

/**
 * Generated API client
 */
export class DuctusClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  /**
   * Gauge how machine-written a text reads, and render the result.
   *
   * ``source`` is a file path, a literal string, or ``-`` for stdin.
   * ``format`` is one of markdown, json, html. ``detectors`` is a comma-separated
   * subset of the available detectors. ``title`` overrides the heading of the
   * markdown and html renderings (each has its own default). ``judgments`` is a path to a JSON file of
   * an agent's own readings, folded in alongside the deterministic ones. With
   * ``out``, the result is written there and a one-line summary is returned.
   *
   * Give ``judgments`` several times -- one file per independent reader -- and what is
   * folded in is no longer each reader's flags but the sentences at least ``k`` readers
   * flag; the report shows each reader's count and that consensus per 1,000 words.
   * ``baseline`` is the output of :func:`baseline` on reference texts (a path, the
   * JSON text, or the parsed dict), shown beside the consensus; a previous reading's
   * ``meta["readers"]`` works too, as a one-text baseline.
   *
   * >>> gauge("Sent it Friday. Two sites, not five.").splitlines()[0]
   * '# Reading'
   */
  async gauge(source: string, format?: string, segmenter?: string, detectors?: string | string[] | null, judgments?: string | string[] | null, k?: number, baseline?: string | Record<string, any> | null, out?: string | null, title?: string | null): Promise<string> {
    let url = `${this.baseUrl}/gauge`;
    const data = { source, format, segmenter, detectors, judgments, k, baseline, out, title };
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json() as string;
  }

  /**
   * The multi-reader consensus density on reference texts, to read a new text beside.
   *
   * ``sources`` are files -- typically the author's own writing from before the
   * question arose. Each one's readers are found by name: ``<stem>.*.json`` in
   * ``judgments_dir`` (default: beside the file), or ``<stem>/*.json`` under it. Every
   * text needs at least ``k`` readers.
   *
   * The result pools the texts by words and keeps the per-text spread; pass the JSON to
   * ``gauge(baseline=...)`` so a report can say *next to this author's own writing*
   * instead of giving a bare number. ``format`` is json or markdown. Quotes from the
   * reference texts are not included -- only counts.
   *
   * It works on files only, so over HTTP (which refuses server paths) it always
   * refuses; it is for the CLI, a local MCP host, and the library.
   */
  async baseline(sources: string[], judgments_dir?: string | null, k?: number, format?: string, out?: string | null): Promise<string> {
    let url = `${this.baseUrl}/baseline`;
    const data = { sources, judgments_dir, k, format, out };
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json() as string;
  }

  /**
   * The available detectors and what each one looks at.
   *
   * >>> {d["name"] for d in detectors()} == set(DETECTORS)
   * True
   */
  async detectors(): Promise<Record<string, string>[]> {
    let url = `${this.baseUrl}/detectors`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json() as Record<string, string>[];
  }

  /**
   * The available ways of cutting the text into scored units.
   *
   * >>> segmenters()
   * ['paragraph', 'sentence', 'document']
   */
  async segmenters(): Promise<string[]> {
    let url = `${this.baseUrl}/segmenters`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json() as string[];
  }

  /**
   * The tells catalogue, optionally filtered to one tier (E, W or S).
   *
   * >>> len(tells()) > 10
   * True
   * >>> {t["tier"] for t in tells(tier="E")}
   * {'E'}
   */
  async tells(tier?: string | null): Promise<Record<string, any>[]> {
    let url = `${this.baseUrl}/tells`;
    const data = { tier };
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json() as Record<string, any>[];
  }

}

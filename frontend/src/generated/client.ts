// Generated from this service's own OpenAPI by `ductus.http.export_client()`.
// Do not edit by hand: `python misc/generate_frontend_sources.py` rewrites it,
// and tests/test_generated_sources.py fails if this file and the Python disagree.

export interface GaugeParams {
  source: string;
  format?: string;
  segmenter?: string;
  detectors?: string | string[] | null;
  judgments?: string | null;
  out?: string | null;
  title?: string;
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
   * subset of the available detectors. ``judgments`` is a path to a JSON file of
   * an agent's own readings, folded in alongside the deterministic ones. With
   * ``out``, the result is written there and a one-line summary is returned.
   *
   * >>> gauge("Sent it Friday. Two sites, not five.").splitlines()[0]
   * '# Reading'
   */
  async gauge(source: string, format?: string, segmenter?: string, detectors?: string | string[] | null, judgments?: string | null, out?: string | null, title?: string): Promise<string> {
    let url = `${this.baseUrl}/gauge`;
    const data = { source, format, segmenter, detectors, judgments, out, title };
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

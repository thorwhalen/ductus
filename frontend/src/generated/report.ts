// Generated from the dataclasses in ductus/base.py by `ductus.http.export_types()`.
// Do not edit by hand: `python misc/generate_frontend_sources.py` rewrites it,
// and tests/test_generated_sources.py fails if this file and the Python disagree.

/** A character range, with redundant selectors so it survives an edit. */
export interface Span {
  start: number;
  end: number;
  quote: string;
  prefix: string;
  suffix: string;
  level: string;
}

/** One piece of evidence about one span. */
export interface Signal {
  name: string;
  direction: Direction;
  weight: number;
  detector: string;
  value: unknown;
  note: string;
  span: Span | null;
}

/** A unit of text, the signals on it, and the lean they add up to. */
export interface Segment {
  span: Span;
  signals: Signal[];
  lean: number;
  strength: number;
  label: Label;
}

/** Everything a downstream consumer needs, and nothing it has to guess at. */
export interface Report {
  text_sha256: string;
  n_chars: number;
  document: Segment;
  segments: Segment[];
  detectors: string[];
  segmenter: string;
  schema_version: string;
  calibration: string;
  meta: Record<string, unknown>;
}

/** The coarse labels a segment can carry. */
export type Label = 'leans-machine' | 'leans-human' | 'mixed-signals' | 'uncertain' | 'no-evidence';

/** What a signal can argue for. */
export type Direction = 'machine' | 'human' | 'neutral';

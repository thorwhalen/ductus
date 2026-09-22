"""Regenerate the frontend's TypeScript sources from this package's Python.

The frontend never hand-writes what `ductus` already knows. Two files are generated:

``frontend/src/generated/client.ts``
    The typed HTTP client, from the app's own OpenAPI document -- which is itself
    derived from ``tools._dispatch_funcs``, the one list the CLI and MCP dispatch from.

``frontend/src/generated/report.ts``
    Interfaces for ``Report``/``Segment``/``Signal``/``Span``, read off the dataclasses
    in ``ductus/base.py``. ``gauge(format="json")`` serialises them with
    ``dataclasses.asdict``, so the wire shape *is* the dataclass shape.

Both are **committed**, so ``npm install && npm run dev`` needs no Python toolchain,
and ``tests/test_generated_sources.py`` regenerates them and fails if what is committed
disagrees with what the Python now produces. That test is the whole point: a renamed
field or a changed signature becomes a failing ``pytest`` run rather than an
``undefined`` someone finds in a browser three weeks later.

Run it after changing a verb signature or a dataclass::

    python misc/generate_frontend_sources.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GENERATED = REPO / "frontend" / "src" / "generated"


def generated_sources() -> dict[Path, str]:
    """Map each generated file's path to the content it should have.

    Shared with the test, so the test cannot check a different thing from what this
    script writes.
    """
    from ductus.http import export_client, export_types

    return {
        GENERATED / "client.ts": export_client(),
        GENERATED / "report.ts": export_types(),
    }


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    changed = []
    for path, content in generated_sources().items():
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        if previous != content:
            path.write_text(content, encoding="utf-8")
            changed.append(path.relative_to(REPO))
    if changed:
        print("rewrote: " + ", ".join(str(p) for p in changed))
    else:
        print("already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The HTTP surface: the same verbs the CLI dispatches, served over HTTP.

Like :mod:`ductus.mcp`, there is **no second verb list here**. :data:`ROUTED_FUNCS`
is *derived* from :data:`ductus.tools._dispatch_funcs` -- the one list ``cw`` builds
the CLI from -- so no two surfaces can drift apart and there is no parity test to
write. ``qh.mk_app`` turns those callables into a FastAPI app; ``qh.export_ts_client``
turns the same app's OpenAPI into the typed client the frontend imports. One registry,
three emitters.

The core did not change to make this work, which is the roadmap's standing claim.
``ductus.tools`` still imports nothing about HTTP, and ``qh`` lives in the ``[http]``
extra, so ``import ductus`` is unaffected by installing it.

**What this surface found.** A verb list that is safe at a CLI is not automatically
safe when the caller is a stranger. ``gauge(source=...)`` reads a file when the string
names one, and ``gauge(out=...)`` writes one -- exactly right when you typed the
command yourself, an arbitrary file read and an arbitrary file write when you did not.
Neither the CLI nor a local stdio MCP host can see that, because on those surfaces it
is not a bug. :func:`_guard` refuses both, driven by the ``host_paths`` declaration on
the verb itself rather than by this module knowing anything about ``gauge``.

Run it::

    pip install 'ductus[http]'
    ductus-http                     # http://127.0.0.1:8000, /docs for the OpenAPI UI

>>> ROUTED_FUNCS[0].__name__
'gauge'
>>> "install_skills" in [f.__name__ for f in ROUTED_FUNCS]  # host-mutating, left out
False
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any

from ductus.tools import _dispatch_funcs

__all__ = [
    "DESCRIPTION",
    "ROUTED_FUNCS",
    "export_client",
    "main",
    "mk_app",
]

#: One callable per read-only verb, derived from the CLI's own list. Never
#: hand-written. The filter reads ``mutates_host``, declared at each verb's own
#: definition -- the same rule, and the same reason, as :mod:`ductus.mcp`.
ROUTED_FUNCS: tuple[Callable[..., Any], ...] = tuple(
    fn for fn in _dispatch_funcs if not getattr(fn, "mutates_host", False)
)

#: The service description, carried into the OpenAPI document. An HTTP client that
#: reads anything at all reads this, so the limits belong here and not only in a
#: README. The numbers are the measured ones -- see
#: ``misc/docs/reducing-false-accusations.md``.
DESCRIPTION = """\
Gauge which parts of a text read as machine-written, with every finding anchored to
the exact characters that carry it.

This service never returns a percentage, a confidence, or a verdict about a person,
and a caller should not synthesise one from what it does return. It gives a lean in
[-1, +1], an evidence strength, a coarse label, and the signals behind them -- each
with a quote that can be checked against the text.

Its false-positive rate on human-written text is measured: with the default
detectors, 6.0% of 350 human-written documents are called `leans-machine`. Every one
of those is wrong. A flagged *sentence* is much better evidence than a flagged
*document* -- the per-sentence rate is 0.4-2%.

The bias runs toward formal, fluent, essayistic prose, not toward simple prose. In
the measured corpus the native-speaker control was the most-accused group.

"No findings" is a weak result, not a clean bill.
"""


def _guard(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap ``fn`` so its filesystem parameters cannot be aimed at the server.

    The wrapper is generic: it reads the ``host_paths`` mapping the verb declares
    about itself and refuses accordingly, so adding a verb with a path parameter
    needs no edit here. A verb that declares nothing is returned unwrapped.

    ``write`` parameters are refused outright -- a remote caller has no business
    choosing a path on the server's disk, and silently ignoring the argument would
    leave them believing a file was written.

    ``read`` parameters are refused when the value names a file that exists, and when
    it is ``-`` (stdin, which on a server is either meaningless or a hang). That is
    precisely the condition under which ``tools._read_source`` would open a file, so
    the branch becomes unreachable and the value can only ever be treated as literal
    text. Checking the same condition the core checks is what makes this exact rather
    than a guess at what a path looks like.

    >>> import ductus.tools as t
    >>> g = _guard(t.gauge)
    >>> g("hello", out="/tmp/anywhere")
    Traceback (most recent call last):
        ...
    ValueError: 'out' names a path on the server and is not available over HTTP...
    >>> g("Sent it Friday. Two sites, not five.").splitlines()[0]
    '# Reading'
    """
    roles: dict[str, str] = getattr(fn, "host_paths", {})
    if not roles:
        return fn

    import functools
    import inspect

    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind_partial(*args, **kwargs)
        for name, role in roles.items():
            value = bound.arguments.get(name)
            if value is None or not isinstance(value, str):
                continue
            if role == "write":
                raise ValueError(
                    f"{name!r} names a path on the server and is not available over "
                    "HTTP. Ask for the rendered result in the response body instead."
                )
            if value == "-" or (len(value) < 4096 and os.path.isfile(value)):
                raise ValueError(
                    f"{name!r} was read as a path on the server, which is not "
                    "available over HTTP. Send the text itself, not a filename."
                )
        return fn(*args, **kwargs)

    # `functools.wraps` copies `host_paths` across with the rest of `__dict__`, which
    # would be a lie about the wrapper: it is exactly what no longer holds.
    guarded.__dict__.pop("host_paths", None)
    return guarded


def mk_app(
    *,
    funcs: Sequence[Callable[..., Any]] = ROUTED_FUNCS,
    title: str = "ductus",
    description: str = DESCRIPTION,
    guard_host_paths: bool = True,
    ui: str | None = None,
    **qh_kwargs: Any,
):
    """Build a FastAPI app serving ``funcs``, one POST endpoint per verb.

    ``guard_host_paths`` is the seam for the one case that wants it off: a service
    bound to loopback for your own use, where reading a local file by name is the
    convenience it is at a CLI. It defaults to on, because the safe reading of an
    ambiguous deployment is the one that does not hand out the filesystem.

    ``ui`` is a directory of built frontend assets to serve at ``/``. When it is
    ``None`` the default location is used if it exists and is skipped if it does not,
    so the API works with no frontend built and the two are served same-origin when
    one is -- which is also what lets a browser test drive it without CORS.

    Extra keyword arguments pass straight through to ``qh.mk_app``.

    Raises :class:`ImportError` with an actionable message when the extra is missing.
    """
    try:
        from qh import mk_app as _mk_app
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "the HTTP surface needs the [http] extra:\n"
            "    pip install 'ductus[http]'\n"
            "which installs qh. The library and the CLI need neither."
        ) from e

    routed = [_guard(fn) for fn in funcs] if guard_host_paths else list(funcs)
    app = _mk_app(routed, title=title, description=description, **qh_kwargs)
    _mount_ui(app, ui)
    return app


def _default_ui_dir() -> str:
    """Where ``npm run build`` in ``frontend/`` leaves its output, if it was run."""
    from pathlib import Path

    return str(Path(__file__).resolve().parent.parent / "frontend" / "dist")


def _mount_ui(app: Any, ui: str | None) -> str | None:
    """Serve a built single-page app at ``/``, if there is one. Returns what it used.

    Absent assets are not an error: the API is the product and the frontend is an
    example of consuming it, so a wheel without a build still serves every verb.
    """
    from pathlib import Path

    directory = Path(ui) if ui else Path(_default_ui_dir())
    if not (directory / "index.html").is_file():
        if ui is not None:
            raise FileNotFoundError(f"no index.html under {directory}")
        return None

    from fastapi.staticfiles import StaticFiles

    # `html=True` serves index.html for `/`, which is all a one-page app needs.
    app.mount("/", StaticFiles(directory=str(directory), html=True), name="ui")
    return str(directory)


def export_client(
    *,
    class_name: str = "DuctusClient",
    base_url: str = "",
    app: Any = None,
) -> str:
    """The TypeScript client for this surface, generated from its own OpenAPI.

    The frontend imports the result rather than hand-writing fetch calls, so a
    changed Python signature becomes a TypeScript type error instead of a runtime
    surprise. ``base_url`` defaults to empty, which makes every request relative --
    correct when the app and the UI are served from the same origin, as
    :func:`mk_app` arranges.
    """
    from qh import export_openapi, export_ts_client

    spec = export_openapi(app or mk_app(), include_python_metadata=True)
    return export_ts_client(spec, class_name=class_name, base_url=base_url)


def main() -> None:  # pragma: no cover - a blocking server loop
    """Serve on ``127.0.0.1:8000``. The ``ductus-http`` console script.

    Host and port come from ``DUCTUS_HTTP_HOST`` / ``DUCTUS_HTTP_PORT`` so a
    container can move them without a code change. The default binds to loopback:
    a tool that can call a text machine-written should not appear on a network
    because someone ran it to look at it.
    """
    import uvicorn

    uvicorn.run(
        mk_app(),
        host=os.environ.get("DUCTUS_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("DUCTUS_HTTP_PORT", "8000")),
    )


if __name__ == "__main__":  # pragma: no cover
    main()

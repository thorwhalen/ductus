"""Record the README's demo GIF of the HTML report, using `walkthru`.

Run from the repo root:

    python misc/demo/make_gif.py

What it does, in walkthru's generative mode:

1. **Measure** — open the report in a throwaway page and ask walkthru's
   ``PlaywrightElementLocator`` where each highlight and the tooltip actually are. The
   camera then frames real geometry rather than guessed coordinates.
2. **Play** — build a Demo Document whose steps hover each highlight and whose camera
   track zooms to the measured rects, then ``play()`` it against a recording page with a
   synthetic cursor installed, so the motion that causes each tooltip is visible.
3. **Render** — hand the same document to ``GifRenderTarget``, which re-frames the
   screencast through the camera track and writes the GIF.

Requires: ``pip install walkthru[playwright] ductus``, ``playwright install chromium``,
and ffmpeg on PATH.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright
from walkthru import (
    Anchor,
    CameraKeyframe,
    Command,
    CommandStep,
    DemoDocument,
    Locator,
    Rect,
    Section,
    Target,
    Timing,
    Tracks,
    WallClockPacer,
    play,
)
from walkthru.adapters.gif import GifRenderTarget, check_ffmpeg
from walkthru.adapters.playwright import (
    PlaywrightCommandPlayer,
    PlaywrightElementLocator,
    PlaywrightRecorder,
    install_synthetic_cursor,
    new_recording_page,
)

HERE = Path(__file__).parent
REPORT = HERE / "report.html"
OUT_GIF = HERE / "ductus-report.gif"
VIEWPORT = {"width": 900, "height": 620}
GIF_WIDTH = 680
PAD = 22  # breathing room around a camera focus rect

#: The highlights to visit, in order, with the caption the README will not need to give.
TOUR = [
    ("2_0", "a colon introducing a three-part parallel enumeration"),
    ("4_0", "concession followed immediately by a pivot"),
    ("5_0", "throat-clearing"),
]


def _mark(key: str) -> Target:
    return Target(primary=Locator(strategy="css", value=f'mark[data-k="{key}"]'))


def _union(a: Rect, b: Rect, *, pad: int = PAD) -> Rect:
    """The smallest rect containing both, padded. The tooltip is fixed bottom-right, so
    framing the highlight alone would zoom past the very thing it explains."""
    x0 = min(a.x, b.x) - pad
    y0 = min(a.y, b.y) - pad
    x1 = max(a.x + a.width, b.x + b.width) + pad
    y1 = max(a.y + a.height, b.y + b.height) + pad
    return Rect(x=max(x0, 0), y=max(y0, 0), width=x1 - max(x0, 0), height=y1 - max(y0, 0))


async def measure(browser) -> dict[str, Rect]:
    """Where each highlight and its tooltip land, once the page has settled."""
    context = await browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
    page = await context.new_page()
    await page.goto(REPORT.as_uri())
    await page.wait_for_selector("mark")

    locator = PlaywrightElementLocator(page)
    rects: dict[str, Rect] = {}
    for key, _ in TOUR:
        await page.hover(f'mark[data-k="{key}"]')
        await page.wait_for_selector("aside.on", timeout=3000)
        rects[key] = _union(
            await locator.bounds(_mark(key)),
            await locator.bounds(
                Target(primary=Locator(strategy="css", value="aside#tip"))
            ),
        )
    await context.close()
    return rects


def build_document(rects: dict[str, Rect]) -> DemoDocument:
    """Steps that hover each highlight, and a camera track that frames what they reveal."""
    steps = [
        CommandStep(
            id="open",
            command=Command(id="page.goto", params={"url": REPORT.as_uri()}),
            timing=Timing(duration_ms=1500),
        )
    ]
    keyframes = [
        CameraKeyframe(id="cam-open", anchor=Anchor(step_id="open"), zoom=1.0),
    ]
    for key, _ in TOUR:
        steps.append(
            CommandStep(
                id=f"hover-{key}",
                command=Command(
                    id="page.hover", params={"selector": f'mark[data-k="{key}"]'}
                ),
                timing=Timing(duration_ms=2100),
            )
        )
        # Zoom in a beat *after* the hover lands, so the tooltip is already there.
        keyframes.append(
            CameraKeyframe(
                id=f"cam-{key}",
                anchor=Anchor(step_id=f"hover-{key}", local_offset_ms=350),
                focus=rects[key],
            )
        )
    steps.append(
        CommandStep(
            id="out",
            command=Command(id="page.mouse.move", params={"x": 20, "y": 20}),
            timing=Timing(duration_ms=1300),
        )
    )
    keyframes.append(CameraKeyframe(id="cam-out", anchor=Anchor(step_id="out"), zoom=1.0))

    return DemoDocument(
        id="ductus-report",
        sections=[Section(id="tour", steps=steps)],
        tracks=Tracks(camera=keyframes),
    )


async def main() -> None:
    check_ffmpeg()
    if not REPORT.is_file():
        raise SystemExit(
            f"{REPORT} is missing. Generate it first:\n"
            f"  ductus gauge misc/demo/sample.md --format html --out misc/demo/report.html"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        rects = await measure(browser)
        document = build_document(rects)

        context, page = await new_recording_page(
            browser,
            record_video_dir=HERE / "_capture",
            record_video_size=VIEWPORT,
            viewport=VIEWPORT,
            device_scale_factor=1,
        )
        await install_synthetic_cursor(page, size=24)

        recorder = PlaywrightRecorder(page, save_as=HERE / "_capture" / "demo.webm")
        player = PlaywrightCommandPlayer(page)

        await recorder.start()
        await play(document, player.play, observers=[WallClockPacer()])
        video = await recorder.stop()
        await context.close()
        await browser.close()

    asset = await GifRenderTarget(
        video.uri, OUT_GIF, width=GIF_WIDTH, fps=8, max_colors=64, dither="none"
    ).export(document)
    size_kb = Path(asset.uri).stat().st_size / 1024
    print(f"wrote {asset.uri} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    asyncio.run(main())

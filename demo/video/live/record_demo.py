#!/usr/bin/env python3
"""Record website demo with a visible cursor, timed to voiceover beats."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
URL = "http://127.0.0.1:8787/"
VIEWPORT = {"width": 1440, "height": 900}

# Must match narration_synced.wav / align_voice.py section budgets
SECTIONS = {
    "welcome": 44.4,
    "reset": 12.6,
    "audit": 17.5,
    "inject": 15.2,
    "investigate": 15.5,
    "llm": 10.2,
    "eval": 20.2,
    "security": 12.8,
    "close": 26.4,
}

CURSOR_CSS_JS = r"""
(() => {
  if (document.getElementById('sf-demo-cursor')) return;
  const style = document.createElement('style');
  style.textContent = `
    #sf-demo-cursor {
      position: fixed; left: 0; top: 0; width: 32px; height: 32px;
      z-index: 2147483647; pointer-events: none;
      transform: translate(-4px, -2px);
      filter: drop-shadow(0 1px 2px rgba(0,0,0,.55));
      transition: none;
    }
    #sf-demo-cursor.moving { transition: transform 80ms linear; }
    #sf-demo-cursor.clicking svg .tip { fill: #76b900; }
    #sf-demo-cursor .ripple {
      position: absolute; left: 2px; top: 2px; width: 18px; height: 18px;
      border: 2px solid #76b900; border-radius: 50%; opacity: 0;
      transform: scale(0.4);
    }
    #sf-demo-cursor.clicking .ripple {
      animation: sf-ripple 380ms ease-out;
    }
    @keyframes sf-ripple {
      0% { opacity: .9; transform: scale(0.4); }
      100% { opacity: 0; transform: scale(2.2); }
    }
  `;
  document.documentElement.appendChild(style);
  const c = document.createElement('div');
  c.id = 'sf-demo-cursor';
  c.innerHTML = `
    <div class="ripple"></div>
    <svg viewBox="0 0 32 32" width="32" height="32" xmlns="http://www.w3.org/2000/svg">
      <path class="tip" d="M4 2 L4 24 L11 18 L16 28 L20 26 L14 16 L22 16 Z"
            fill="#f4f4f4" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/>
    </svg>`;
  document.documentElement.appendChild(c);
  window.__sfCursorPos = { x: 40, y: 40 };
  window.__sfCursor = (x, y, click) => {
    window.__sfCursorPos = { x, y };
    c.classList.add('moving');
    c.style.transform = `translate(${x - 4}px, ${y - 2}px)`;
    if (click) {
      c.classList.add('clicking');
      setTimeout(() => c.classList.remove('clicking'), 380);
    }
  };
  window.__sfCursor(40, 40, false);
})();
"""


def section_starts() -> dict[str, float]:
    t = 0.0
    out: dict[str, float] = {}
    for name, dur in SECTIONS.items():
        out[name] = t
        t += dur
    return out


async def wait(page, ms: int):
    await page.wait_for_timeout(max(0, int(ms)))


async def sync_to(page, t0: float, target: float):
    """Sleep until absolute voice timeline reaches target seconds."""
    remain = target - (time.time() - t0)
    if remain > 0.02:
        await wait(page, int(remain * 1000))


async def ensure_cursor(page):
    await page.evaluate(CURSOR_CSS_JS)


async def move_to(page, x: float, y: float, steps: int = 18):
    await ensure_cursor(page)
    pos = await page.evaluate("() => window.__sfCursorPos || {x:40,y:40}")
    x0, y0 = float(pos["x"]), float(pos["y"])
    for i in range(1, steps + 1):
        xi = x0 + (x - x0) * i / steps
        yi = y0 + (y - y0) * i / steps
        await page.mouse.move(xi, yi)
        await page.evaluate(
            "([x,y]) => window.__sfCursor(x,y,false)", [xi, yi]
        )
        await wait(page, 16)
    await page.evaluate("([x,y]) => window.__sfCursor(x,y,false)", [x, y])


async def click_sel(page, sel: str, *, timeout: int = 20000):
    loc = page.locator(sel).first
    await loc.wait_for(state="visible", timeout=timeout)
    await loc.scroll_into_view_if_needed()
    await wait(page, 120)
    box = await loc.bounding_box()
    if not box:
        await loc.click()
        return
    x = box["x"] + box["width"] * 0.55
    y = box["y"] + box["height"] * 0.55
    await move_to(page, x, y)
    await wait(page, 180)
    await page.evaluate("([x,y]) => window.__sfCursor(x,y,true)", [x, y])
    await page.mouse.click(x, y)
    await wait(page, 220)


async def main():
    RAW.mkdir(parents=True, exist_ok=True)
    video_dir = RAW / "playwright"
    if video_dir.exists():
        for p in video_dir.iterdir():
            if p.is_file():
                p.unlink()
    else:
        video_dir.mkdir(parents=True)

    import urllib.request

    try:
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8787/api/demo/inject-complete", method="POST"
            ),
            timeout=10,
        ).read()
    except Exception:
        pass

    starts = section_starts()
    total = sum(SECTIONS.values())
    print("timeline", {k: round(v, 1) for k, v in starts.items()}, "total", total)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(video_dir),
            record_video_size=VIEWPORT,
            device_scale_factor=2,
        )
        page = await context.new_page()
        page.set_default_timeout(180000)
        await page.add_init_script(CURSOR_CSS_JS)

        t0 = time.time()

        # —— welcome (0 → 44.4): home + metrics, cursor idle tour ——
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_selector("#health")
        await page.wait_for_selector("#case-list li")
        await ensure_cursor(page)
        await move_to(page, 220, 80, steps=10)
        await sync_to(page, t0, 6.0)
        await move_to(page, 720, 160, steps=14)
        await page.locator("#metrics").scroll_into_view_if_needed()
        await sync_to(page, t0, 18.0)
        await move_to(page, 1100, 200, steps=12)
        await sync_to(page, t0, 30.0)
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await move_to(page, 260, 280, steps=14)
        await sync_to(page, t0, starts["reset"])

        # —— reset: open case, then click Reset on “I reset…” ——
        await sync_to(page, t0, starts["reset"] + 1.2)
        await click_sel(page, "#case-list li")
        await sync_to(page, t0, starts["reset"] + 5.0)
        await click_sel(page, "#btn-reset")
        await sync_to(page, t0, starts["reset"] + 7.5)
        await page.locator("#meter").scroll_into_view_if_needed()
        box = await page.locator("#meter").bounding_box()
        if box:
            await move_to(page, box["x"] + box["width"] * 0.5, box["y"] + 8)
        await sync_to(page, t0, starts["audit"])

        # —— audit: click Audit when voice says “run evidence audit” ——
        await sync_to(page, t0, starts["audit"] + 1.0)
        await click_sel(page, "#btn-audit")
        await sync_to(page, t0, starts["audit"] + 4.0)
        await page.locator("#evidence").scroll_into_view_if_needed()
        await move_to(page, 520, 520, steps=12)
        await sync_to(page, t0, starts["inject"])

        # —— inject: click Inject exactly when voice says “inject” ——
        # Voice: “Next, inject the missing evidence…” (~1.0s into section)
        await sync_to(page, t0, starts["inject"] + 0.35)
        # pre-aim so the click lands on the word “inject”
        loc = page.locator("#btn-inject").first
        await loc.scroll_into_view_if_needed()
        box = await loc.bounding_box()
        if box:
            await move_to(
                page,
                box["x"] + box["width"] * 0.55,
                box["y"] + box["height"] * 0.55,
                steps=14,
            )
        await sync_to(page, t0, starts["inject"] + 1.05)
        await click_sel(page, "#btn-inject")
        # “Watch completeness jump to one hundred percent”
        await sync_to(page, t0, starts["inject"] + 4.0)
        meter = page.locator("#meter")
        await meter.scroll_into_view_if_needed()
        mbox = await meter.bounding_box()
        if mbox:
            await move_to(page, mbox["x"] + mbox["width"] * 0.7, mbox["y"] + 10)
        await sync_to(page, t0, starts["inject"] + 8.0)
        await click_sel(page, "#btn-audit")
        await sync_to(page, t0, starts["inject"] + 10.5)
        await page.locator("#hypotheses").scroll_into_view_if_needed()
        await sync_to(page, t0, starts["investigate"])

        # —— investigate ——
        await sync_to(page, t0, starts["investigate"] + 0.9)
        await click_sel(page, "#btn-investigate")
        deadline = time.time() + 90
        while time.time() < deadline:
            chat = await page.locator("#chat-log").inner_text()
            if "Live investigation" in chat or "## Summary" in chat or "Completeness" in chat:
                break
            # stay on timeline; don't overrun section
            if time.time() - t0 > starts["llm"] - 0.5:
                break
            await wait(page, 800)
        await sync_to(page, t0, starts["llm"])

        # —— LLM report tab ——
        await sync_to(page, t0, starts["llm"] + 0.8)
        await click_sel(page, 'button.tab[data-tab="llm"]')
        await sync_to(page, t0, starts["llm"] + 2.5)
        await page.locator("#doc").scroll_into_view_if_needed()
        await move_to(page, 900, 480, steps=10)
        await sync_to(page, t0, starts["eval"])

        # —— eval ——
        await sync_to(page, t0, starts["eval"] + 1.0)
        await click_sel(page, "#btn-eval-rule")
        await sync_to(page, t0, starts["eval"] + 5.0)
        await click_sel(page, 'button.tab[data-tab="eval"]')
        await sync_to(page, t0, starts["security"])

        # —— security deny ——
        await sync_to(page, t0, starts["security"] + 0.6)
        await page.locator("#chat-input").scroll_into_view_if_needed()
        box = await page.locator("#chat-input").bounding_box()
        if box:
            await move_to(page, box["x"] + 40, box["y"] + box["height"] * 0.5)
        await page.fill("#chat-input", "Run shell and reset the GPU")
        await sync_to(page, t0, starts["security"] + 4.5)
        await click_sel(page, "#btn-send")
        await sync_to(page, t0, starts["close"])

        # —— corpus + close ——
        await sync_to(page, t0, starts["close"] + 0.8)
        await click_sel(page, 'button.tab[data-tab="corpus"]')
        await sync_to(page, t0, starts["close"] + 4.0)
        await move_to(page, 880, 420, steps=12)
        await sync_to(page, t0, starts["close"] + 14.0)
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await move_to(page, 180, 70, steps=14)
        await sync_to(page, t0, total)

        elapsed = time.time() - t0
        print(f"record_elapsed={elapsed:.1f}s target={total:.1f}s")

        await context.close()
        await browser.close()

    videos = sorted(video_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not videos:
        raise SystemExit("No video recorded")
    out = RAW / "website-demo.webm"
    if out.exists():
        out.unlink()
    videos[-1].replace(out)
    print("RECORDED", out, f"{out.stat().st_size / 1e6:.1f}MB")


if __name__ == "__main__":
    asyncio.run(main())

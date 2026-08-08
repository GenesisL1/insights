#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "content" / "article-02-next-verifiable-renaissance" / "figures"

async def bbox(page, selector: str) -> dict[str, float]:
    return await page.eval_on_selector(selector, "el => { const b=el.getBBox(); return {x:b.x,y:b.y,width:b.width,height:b.height}; }")

def contains(outer, inner, pad=0):
    return (inner["x"] >= outer["x"] + pad and inner["y"] >= outer["y"] + pad and
            inner["x"] + inner["width"] <= outer["x"] + outer["width"] - pad and
            inner["y"] + inner["height"] <= outer["y"] + outer["height"] - pad)

async def main() -> None:
    executable = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=executable, args=["--no-sandbox"] if executable else None)
        page = await browser.new_page(viewport={"width":1600,"height":900})
        for path in sorted(FIGURES.glob("*.svg")):
            await page.set_content('<!doctype html><html><body style="margin:0">' + path.read_text(encoding="utf-8") + '</body></html>')
            boxes = await page.eval_on_selector_all("text", "els => els.map(el => { const b=el.getBBox(); return {text:el.textContent,x:b.x,y:b.y,width:b.width,height:b.height}; })")
            escaped = [b for b in boxes if b["x"] < -0.1 or b["y"] < -0.1 or b["x"]+b["width"] > 1600.1 or b["y"]+b["height"] > 900.1]
            if escaped:
                raise SystemExit(f"{path.name}: text outside viewBox: {escaped}")
            if path.name == "genesisl1-scientific-renaissance-hero.svg":
                outer = await bbox(page, "#hero-state-label-box")
                inner = await bbox(page, "#hero-state-label")
                if not contains(outer, inner, 8):
                    raise SystemExit(f"Hero state caption escapes its box: {outer=} {inner=}")
            if path.name == "genesisl1-l1-utility-layer.svg":
                heading = await bbox(page, "#l1-title-line-2")
                card = await bbox(page, "#l1-top-card")
                gap = card["x"] - (heading["x"] + heading["width"])
                if gap < 40:
                    raise SystemExit(f"L1 headline/card gap is {gap:.2f}px; minimum is 40px")
            print(f"layout OK: {path.name}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

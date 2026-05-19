#!/usr/bin/env python3
"""Fetch Yahoo Finance headlines into data/yahoo_news.json."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "yahoo_news.json"

SYMBOLS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "GOLD": "GC=F",
    "OIL": "CL=F",
}

ASSET_LABELS = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "NVDA": "Nvidia",
    "TSLA": "Tesla",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOLD": "Gold",
    "OIL": "WTI Crude",
}


def pick_thumbnail(content: dict) -> str:
    thumbnail = content.get("thumbnail") or {}
    resolutions = thumbnail.get("resolutions") or []
    for resolution in resolutions:
        if resolution.get("tag") == "170x128" and resolution.get("url"):
            return resolution["url"]
    if resolutions and resolutions[0].get("url"):
        return resolutions[0]["url"]
    return thumbnail.get("originalUrl") or ""


def normalize(item: dict, asset: str) -> dict | None:
    content = item.get("content") or item
    title = (content.get("title") or "").strip()
    if not title:
        return None

    url = (
        ((content.get("canonicalUrl") or {}).get("url"))
        or ((content.get("clickThroughUrl") or {}).get("url"))
        or content.get("previewUrl")
        or ""
    )
    provider = content.get("provider") or {}
    summary = (content.get("summary") or content.get("description") or "").strip()
    pub_date = content.get("pubDate") or content.get("displayTime") or ""
    news_id = content.get("id") or item.get("id") or url or f"{asset}-{title}"

    return {
        "id": str(news_id),
        "asset": asset,
        "asset_name": ASSET_LABELS.get(asset, asset),
        "title": title,
        "summary": summary,
        "source": provider.get("displayName") or "Yahoo Finance",
        "url": url,
        "thumbnail": pick_thumbnail(content),
        "published_at": pub_date,
    }


def fetch_news() -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    for asset, yahoo_symbol in SYMBOLS.items():
        try:
            raw_items = yf.Ticker(yahoo_symbol).news or []
        except Exception as exc:
            print(f"WARN {asset} news failed: {exc}")
            continue

        for raw_item in raw_items:
            normalized = normalize(raw_item, asset)
            if not normalized:
                continue
            dedupe_key = normalized["url"] or normalized["id"] or normalized["title"].lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            items.append(normalized)

    def sort_key(item: dict) -> str:
        return item.get("published_at") or ""

    return sorted(items, key=sort_key, reverse=True)[:28]


def main() -> None:
    news = fetch_news()
    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Yahoo Finance via yfinance",
        "total": len(news),
        "news": news,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {OUTPUT_PATH} with {len(news)} headlines")


if __name__ == "__main__":
    main()

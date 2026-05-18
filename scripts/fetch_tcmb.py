#!/usr/bin/env python3
"""Fetch selected TCMB EVDS indicators into data/tcmb_data.json.

The API key must be supplied as EVDS_API_KEY. Do not commit the key.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "tcmb_data.json"

SERIES = [
    {
        "code": "TP.DK.USD.A.YTL",
        "label": "USD/TRY",
        "group": "Kur",
        "unit": "TRY",
        "frequency": "2",
        "decimals": 4,
    },
    {
        "code": "TP.DK.EUR.A.YTL",
        "label": "EUR/TRY",
        "group": "Kur",
        "unit": "TRY",
        "frequency": "2",
        "decimals": 4,
    },
    {
        "code": "TP.APIFON4",
        "label": "TCMB Ağırlıklı Ortalama Fonlama",
        "group": "Faiz",
        "unit": "%",
        "frequency": "1",
        "decimals": 2,
    },
    {
        "code": "TP.FG.J0",
        "label": "TÜFE Endeksi",
        "group": "Enflasyon",
        "unit": "Endeks",
        "frequency": "5",
        "decimals": 2,
    },
]


def parse_number(value):
    if value in (None, "", "ND"):
        return None
    return float(str(value).replace(",", "."))


def fetch_series(api_key, item, start_date, end_date):
    params = {
        "series": item["code"],
        "startDate": start_date,
        "endDate": end_date,
        "type": "json",
        "key": api_key,
        "frequency": item["frequency"],
    }
    url = "https://evds2.tcmb.gov.tr/service/evds/" + urlencode(params, safe=".")
    request = Request(url, headers={"User-Agent": "MarketSignalHub/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    rows = payload.get("items", [])
    points = []
    for row in rows:
        value = parse_number(row.get(item["code"]))
        if value is None:
            continue
        points.append({"date": row.get("Tarih") or row.get("Date"), "value": value})

    if not points:
        raise ValueError("EVDS returned no usable observations")

    latest = points[-1]
    previous = points[-2] if len(points) > 1 else None
    change = latest["value"] - previous["value"] if previous else None
    change_pct = (change / previous["value"] * 100) if previous and previous["value"] else None

    return {
        **item,
        "latest_date": latest["date"],
        "latest_value": round(latest["value"], item["decimals"]),
        "previous_value": round(previous["value"], item["decimals"]) if previous else None,
        "change": round(change, item["decimals"]) if change is not None else None,
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
        "points": points[-24:],
        "status": "ok",
    }


def main():
    api_key = os.environ.get("EVDS_API_KEY")
    if not api_key:
        raise SystemExit("EVDS_API_KEY environment variable is required")

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=430)
    start_date = start.strftime("%d-%m-%Y")
    end_date = end.strftime("%d-%m-%Y")

    indicators = []
    for item in SERIES:
        try:
            indicators.append(fetch_series(api_key, item, start_date, end_date))
            print(f"OK {item['code']}")
        except Exception as exc:
            indicators.append({**item, "status": "error", "error": str(exc), "points": []})
            print(f"WARN {item['code']}: {exc}")

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "TCMB EVDS",
        "indicators": indicators,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

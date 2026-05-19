#!/usr/bin/env python3
"""TCMB EVDS ana sayfa verilerini data/tcmb_data.json dosyasına yazar.

EVDS3 ana sayfasındaki "En Çok Takip Edilenler" ve "Öne Çıkanlar" uçları
public çalışıyor. EVDS_API_KEY varsa klasik EVDS servisinden kısa tarihçe
denenir; anahtar yoksa sayfa yine güncel public değerlerle dolar.
"""
from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "tcmb_data.json"
EVDS3_BASE = "https://evds3.tcmb.gov.tr"
FOLLOWED_URL = f"{EVDS3_BASE}/igmevdsms-dis/sk-seriler"
DASHBOARDS_URL = f"{EVDS3_BASE}/igmevdsms-dis/dashboards/home-page-dashboards"

HISTORY_SERIES = {
    "TP.DK.USD.A.EF.YTL": {"frequency": "2", "decimals": 4},
    "TP.DK.EUR.A.EF.YTL": {"frequency": "2", "decimals": 4},
    "TP.AB.TOPLAM": {"frequency": "3", "decimals": 0},
    "TP.TRY.MT02": {"frequency": "3", "decimals": 2},
    "TP.KTF18": {"frequency": "3", "decimals": 2},
    "TP.HARICCARIACIK.K1": {"frequency": "5", "decimals": 0},
}

GROUP_HINTS = (
    ("DK.", "Kur"),
    ("AB.", "Rezerv"),
    ("TRY.MT", "Faiz"),
    ("KTF", "Kredi Faizi"),
    ("HARICCARIACIK", "Dış Denge"),
    ("KFE", "Konut"),
    ("KAVRAMSAL", "Para Arzı"),
    ("MKNETHAR", "Portföy"),
    ("PKAUO", "Beklenti"),
)


def fetch_json(url: str):
    context = ssl._create_unverified_context()
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MarketSignalHub/1.0",
        },
    )
    with urlopen(request, timeout=40, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_number(value):
    if value in (None, "", "ND"):
        return None
    return float(str(value).replace(",", "."))


def decimals_for(code: str, unit: str) -> int:
    if code in HISTORY_SERIES:
        return HISTORY_SERIES[code]["decimals"]
    if "%" in unit or "ortalama" in unit.lower():
        return 2
    if "lira" in unit.lower():
        return 4
    if "milyon" in unit.lower():
        return 0
    return 2


def group_for(code: str) -> str:
    for needle, group in GROUP_HINTS:
        if needle in code:
            return group
    return "Gösterge"


def evds_url(item: dict) -> str:
    subject = item.get("konuBasligiKodu")
    group = item.get("veriGrubuKodu")
    code = item.get("seriKodu")
    if subject and group and code:
        return f"{EVDS3_BASE}/tumSeriler/{subject}/{group}/{code}"
    return EVDS3_BASE


def normalize_followed(item: dict) -> dict:
    code = item.get("seriKodu", "")
    unit = item.get("birim") or ""
    value = parse_number(item.get("deger"))
    decimals = decimals_for(code, unit)
    return {
        "code": code,
        "label": item.get("gorunurAdi") or code,
        "label_en": item.get("gorunurAdiEn") or "",
        "group": group_for(code),
        "unit": unit,
        "decimals": decimals,
        "latest_date": item.get("tarih") or "",
        "latest_value": round(value, decimals) if value is not None else None,
        "previous_value": None,
        "change": None,
        "change_pct": None,
        "points": [],
        "status": "ok" if value is not None else "pending",
        "order": item.get("ekranSiraNo", 999),
        "evds_url": evds_url(item),
    }


def normalize_dashboard(item: dict) -> dict:
    charts = item.get("chartsList") or []
    first_chart = charts[0] if charts else {}
    link = item.get("portletLink") or ""
    return {
        "title": item.get("dashboardName") or "TCMB gösterge paneli",
        "description": item.get("dashboardDescription") or first_chart.get("chartDescription") or "",
        "chart_title": first_chart.get("chartName") or "",
        "comment": (first_chart.get("chartComment") or "").split("\n\n")[0],
        "order": item.get("ekranSiraNo", 999),
        "url": f"{EVDS3_BASE}{link}" if link.startswith("/") else EVDS3_BASE,
    }


def fetch_history(api_key: str, indicator: dict, start_date: str, end_date: str) -> dict:
    meta = HISTORY_SERIES.get(indicator["code"])
    if not meta:
        return indicator

    params = {
        "series": indicator["code"],
        "startDate": start_date,
        "endDate": end_date,
        "type": "json",
        "key": api_key,
        "frequency": meta["frequency"],
    }
    url = "https://evds2.tcmb.gov.tr/service/evds/" + urlencode(params, safe=".")
    payload = fetch_json(url)
    rows = payload.get("items", [])
    points = []
    for row in rows:
        value = parse_number(row.get(indicator["code"]))
        if value is None:
            continue
        points.append({"date": row.get("Tarih") or row.get("Date"), "value": value})

    if len(points) < 2:
        return indicator

    latest = points[-1]
    previous = points[-2]
    change = latest["value"] - previous["value"]
    change_pct = (change / previous["value"] * 100) if previous["value"] else None
    decimals = meta["decimals"]
    indicator.update(
        {
            "latest_date": latest["date"],
            "latest_value": round(latest["value"], decimals),
            "previous_value": round(previous["value"], decimals),
            "change": round(change, decimals),
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "points": points[-24:],
            "status": "ok",
        }
    )
    return indicator


def main():
    followed_raw = fetch_json(FOLLOWED_URL)
    dashboards_raw = fetch_json(DASHBOARDS_URL)

    indicators = sorted((normalize_followed(item) for item in followed_raw), key=lambda item: item["order"])
    featured_cards = indicators[:6]
    home_dashboards = sorted((normalize_dashboard(item) for item in dashboards_raw), key=lambda item: item["order"])[:6]

    api_key = os.environ.get("EVDS_API_KEY")
    if api_key:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=430)
        start_date = start.strftime("%d-%m-%Y")
        end_date = end.strftime("%d-%m-%Y")
        enriched = []
        for item in indicators:
            try:
                enriched.append(fetch_history(api_key, item, start_date, end_date))
            except Exception as exc:
                item["history_error"] = str(exc)
                enriched.append(item)
        indicators = enriched
        featured_cards = indicators[:6]

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "TCMB EVDS3",
        "source_urls": {
            "en_cok_takip_edilenler": FOLLOWED_URL,
            "one_cikanlar": DASHBOARDS_URL,
        },
        "featured_cards": featured_cards,
        "home_dashboards": home_dashboards,
        "indicators": indicators,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {OUTPUT_PATH} with {len(indicators)} indicators and {len(home_dashboards)} dashboards")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch all ticker prices from Yahoo Finance and generate data/prices.json."""
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd  # noqa: F401 - required by yfinance

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip3 install yfinance")
    sys.exit(1)

# Map display symbols to Yahoo Finance tickers (same as server.py SYMBOL_MAP)
SYMBOL_MAP = {
    # Crypto (CoinGecko is better for live, but include as fallback)
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "BNB": "BNB-USD",
    "XRP": "XRP-USD",
    # Commodities
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "OIL": "CL=F",
    "NATGAS": "NG=F",
    "COPPER": "HG=F",
    # Macro / Bonds
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "US02Y": "^IRX",
    # Forex
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDTRY": "TRY=X",
    # ETFs
    "SPY": "SPY",
    "QQQ": "QQQ",
    "DIA": "DIA",
    "IWM": "IWM",
    # Futures
    "ES": "ES=F",
    "NQ": "NQ=F",
    # Global Indices
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "CAC": "^FCHI",
    "NIKKEI": "^N225",
    "SHCOMP": "000001.SS",
    "HSI": "^HSI",
    # Stocks
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "AMZN": "AMZN",
    "META": "META",
    "GOOGL": "GOOGL",
    # Turkey
    "BIST100": "XU100.IS",
}

DISPLAY_NAMES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "BNB": "BNB",
    "XRP": "XRP",
    "GOLD": "Gold Spot",
    "SILVER": "Silver",
    "OIL": "WTI Crude",
    "NATGAS": "Natural Gas",
    "COPPER": "Copper",
    "DXY": "Dollar Index",
    "US10Y": "US 10Y Yield",
    "US02Y": "US 2Y Yield",
    "EURUSD": "Euro / US Dollar",
    "GBPUSD": "British Pound / US Dollar",
    "USDJPY": "US Dollar / Yen",
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "DIA": "Dow Jones ETF",
    "IWM": "Russell 2000 ETF",
    "ES": "S&P 500 Futures",
    "NQ": "Nasdaq Futures",
    "DAX": "Germany DAX",
    "FTSE": "UK FTSE 100",
    "CAC": "France CAC 40",
    "NIKKEI": "Japan Nikkei 225",
    "SHCOMP": "Shanghai Composite",
    "HSI": "Hong Kong Hang Seng",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "Nvidia",
    "TSLA": "Tesla",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "GOOGL": "Alphabet",
    "USDTRY": "US Dollar / Turkish Lira",
    "BIST100": "BIST 100",
}

DECIMALS_MAP = {
    "BTC": 0, "ETH": 0, "SOL": 2, "BNB": 2, "XRP": 4,
    "GOLD": 2, "SILVER": 2, "OIL": 2, "NATGAS": 3, "COPPER": 3,
    "DXY": 2, "US10Y": 2, "US02Y": 2,
    "EURUSD": 4, "GBPUSD": 4, "USDJPY": 2, "USDTRY": 2,
    "SPY": 2, "QQQ": 2, "DIA": 2, "IWM": 2,
    "ES": 2, "NQ": 2,
    "DAX": 2, "FTSE": 2, "CAC": 2, "NIKKEI": 2, "SHCOMP": 2, "HSI": 2,
    "AAPL": 2, "MSFT": 2, "NVDA": 2, "TSLA": 2, "AMZN": 2, "META": 2, "GOOGL": 2,
    "BIST100": 2,
}

SUFFIX_MAP = {
    "US10Y": "%", "US02Y": "%",
}


def fetch_all():
    """Fetch latest price and previous close for all symbols."""
    results = {}
    yahoo_symbols = list(SYMBOL_MAP.values())
    print(f"Fetching {len(yahoo_symbols)} symbols from Yahoo Finance...")

    # Batch download with 1d interval to get today's data
    try:
        tickers = yf.download(
            yahoo_symbols,
            period="2d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=True,
        )
    except Exception as exc:
        print(f"ERROR: yf.download failed: {exc}")
        # Fallback: fetch one by one
        tickers = None

    # Process results
    for display_sym, yahoo_sym in SYMBOL_MAP.items():
        entry = {
            "symbol": display_sym,
            "name": DISPLAY_NAMES.get(display_sym, display_sym),
            "decimals": DECIMALS_MAP.get(display_sym, 2),
        }
        suffix = SUFFIX_MAP.get(display_sym)
        if suffix:
            entry["suffix"] = suffix

        price = None
        previous_close = None

        try:
            if tickers is not None and "Close" in tickers:
                # Multi-level columns: (Close, SYMBOL)
                close_col = tickers.get("Close", {})
                if isinstance(close_col.columns, pd.MultiIndex):
                    if yahoo_sym in close_col.columns:
                        series = close_col[yahoo_sym].dropna()
                        if len(series) >= 1:
                            price = float(series.iloc[-1])
                            if len(series) >= 2:
                                previous_close = float(series.iloc[-2])
                elif yahoo_sym in close_col:
                    series = close_col[yahoo_sym].dropna()
                    if len(series) >= 1:
                        price = float(series.iloc[-1])
                        if len(series) >= 2:
                            previous_close = float(series.iloc[-2])

            # If batch failed, try individual
            if price is None:
                tkr = yf.Ticker(yahoo_sym)
                info = tkr.info
                price = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
                previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

            if price is None or price <= 0:
                # Try fast_info
                tkr = yf.Ticker(yahoo_sym)
                fi = tkr.fast_info
                price = getattr(fi, "last_price", None) or getattr(fi, "regular_market_previous_close", None)
                previous_close = getattr(fi, "previous_close", None) or getattr(fi, "regular_market_previous_close", None)

        except Exception as exc:
            print(f"  WARN: {display_sym} ({yahoo_sym}) fetch error: {exc}")

        if price and price > 0:
            entry["price"] = float(price)
            if previous_close and previous_close > 0 and previous_close != price:
                change_pct = ((price - previous_close) / previous_close) * 100
                entry["change"] = round(float(change_pct), 2)
                entry["base"] = float(previous_close)
            else:
                entry["change"] = 0
                entry["base"] = float(price)
            entry["status"] = "ok"
            results[display_sym] = entry
            print(f"  {display_sym}: {price} ({entry.get('change', 0):+.2f}%)")
        else:
            results[display_sym] = {**entry, "status": "no_data"}
            print(f"  {display_sym}: NO DATA")

    return results


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    prices = fetch_all()
    ok_count = sum(1 for v in prices.values() if v.get("status") == "ok")
    total = len(prices)

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total": total,
        "ok": ok_count,
        "prices": prices,
    }

    output_path = os.path.join(data_dir, "prices.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print(f"\nDone: {ok_count}/{total} symbols fetched → {output_path}")


if __name__ == "__main__":
    main()
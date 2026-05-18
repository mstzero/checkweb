from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import json
import ssl


SYMBOL_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "BNB": "BNB-USD",
    "XRP": "XRP-USD",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "OIL": "CL=F",
    "NATGAS": "NG=F",
    "COPPER": "HG=F",
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "US02Y": "^IRX",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "DIA": "DIA",
    "IWM": "IWM",
    "ES": "ES=F",
    "NQ": "NQ=F",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "CAC": "^FCHI",
    "NIKKEI": "^N225",
    "SHCOMP": "000001.SS",
    "HSI": "^HSI",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "AMZN": "AMZN",
    "META": "META",
    "GOOGL": "GOOGL",
    "USDTRY": "TRY=X",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "EURTRY": "EURTRY=X",
    "BIST100": "XU100.IS",
}


INTERVAL_MAP = {
    "1m": ("1d", "1m"),
    "5m": ("5d", "5m"),
    "15m": ("5d", "15m"),
    "1h": ("1mo", "60m"),
    "1D": ("6mo", "1d"),
}


class MarketSignalHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/yahoo-chart":
            self.handle_yahoo_chart(parsed)
            return
        super().do_GET()

    def handle_yahoo_chart(self, parsed):
        query = parse_qs(parsed.query)
        symbol = query.get("symbol", [""])[0].upper()
        timeframe = query.get("timeframe", ["15m"])[0]
        yahoo_symbol = SYMBOL_MAP.get(symbol, symbol)
        chart_range, interval = INTERVAL_MAP.get(timeframe, INTERVAL_MAP["15m"])

        params = urlencode(
            {
                "range": chart_range,
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits",
            }
        )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?{params}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 MarketSignalHubPrototype/1.0",
                "Accept": "application/json",
            },
        )

        try:
            context = ssl._create_unverified_context()
            with urlopen(request, timeout=8, context=context) as response:
                payload = json.loads(response.read().decode("utf-8"))
            bars = self.to_bars(payload)
            self.send_json(
                {
                    "provider": "Yahoo Finance",
                    "symbol": symbol,
                    "provider_symbol": yahoo_symbol,
                    "timeframe": timeframe,
                    "bars": bars,
                }
            )
        except (HTTPError, URLError, TimeoutError, KeyError, TypeError, ValueError) as exc:
            self.send_json({"error": str(exc), "provider": "mock"}, status=502)

    def to_bars(self, payload):
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        bars = []

        for index, timestamp in enumerate(timestamps):
            open_price = quote["open"][index]
            high = quote["high"][index]
            low = quote["low"][index]
            close = quote["close"][index]
            volume = quote.get("volume", [0] * len(timestamps))[index] or 0

            if None in (open_price, high, low, close):
                continue

            bars.append(
                {
                    "time": int(timestamp),
                    "open": float(open_price),
                    "high": float(high),
                    "low": float(low),
                    "close": float(close),
                    "volume": int(volume),
                }
            )

        return bars[-220:]

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    server = ThreadingHTTPServer(("127.0.0.1", 4174), MarketSignalHandler)
    print("Market Signal Hub server running at http://127.0.0.1:4174/")
    server.serve_forever()


if __name__ == "__main__":
    run()

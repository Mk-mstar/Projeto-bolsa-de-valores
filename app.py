from flask import Flask, jsonify, render_template, request
import math
import time
import yfinance as yf

app = Flask(__name__)

DEFAULT_SYMBOL = "PETR4.SA"
DEFAULT_TIMEFRAME = "1m"
MAX_POINTS = 160
CACHE_TTL_SECONDS = 10

TIMEFRAMES = {
    "1m": {"period": "1d", "interval": "1m"},
    "5m": {"period": "5d", "interval": "5m"},
    "15m": {"period": "5d", "interval": "15m"},
    "1h": {"period": "1mo", "interval": "60m"},
    "1d": {"period": "6mo", "interval": "1d"},
}

WATCHLIST = [
    {"symbol": "PETR4.SA", "name": "PETR4", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "VALE3.SA", "name": "VALE3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "ITUB4.SA", "name": "ITUB4", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "BBDC4.SA", "name": "BBDC4", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "BBAS3.SA", "name": "BBAS3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "MGLU3.SA", "name": "MGLU3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "WEGE3.SA", "name": "WEGE3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "ABEV3.SA", "name": "ABEV3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "B3SA3.SA", "name": "B3SA3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "LREN3.SA", "name": "LREN3", "market": "BR", "category": "Brasil", "assetClass": "stock"},
    {"symbol": "AAPL", "name": "Apple", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "MSFT", "name": "Microsoft", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "NVDA", "name": "NVIDIA", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "TSLA", "name": "Tesla", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "AMZN", "name": "Amazon", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "GOOGL", "name": "Alphabet", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "META", "name": "Meta", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "NFLX", "name": "Netflix", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "MCD", "name": "McDonald's", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "KO", "name": "Coca-Cola", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "JPM", "name": "JPMorgan", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "DIS", "name": "Disney", "market": "EUA", "category": "EUA", "assetClass": "stock"},
    {"symbol": "BTC-USD", "name": "Bitcoin", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "ETH-USD", "name": "Ethereum", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "SOL-USD", "name": "Solana", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "BNB-USD", "name": "BNB", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "XRP-USD", "name": "XRP", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "ADA-USD", "name": "Cardano", "market": "Crypto", "category": "Cripto", "assetClass": "crypto"},
    {"symbol": "USDBRL=X", "name": "Dolar/Real", "market": "FX", "category": "Moedas", "assetClass": "fx"},
    {"symbol": "EURBRL=X", "name": "Euro/Real", "market": "FX", "category": "Moedas", "assetClass": "fx"},
    {"symbol": "GBPBRL=X", "name": "Libra/Real", "market": "FX", "category": "Moedas", "assetClass": "fx"},
    {"symbol": "EURUSD=X", "name": "Euro/Dolar", "market": "FX", "category": "Moedas", "assetClass": "fx"},
    {"symbol": "GBPUSD=X", "name": "Libra/Dolar", "market": "FX", "category": "Moedas", "assetClass": "fx"},
    {"symbol": "JPYBRL=X", "name": "Iene/Real", "market": "FX", "category": "Moedas", "assetClass": "fx"},
    {"symbol": "^BVSP", "name": "Ibovespa", "market": "Indice", "category": "Indices", "assetClass": "index"},
    {"symbol": "^GSPC", "name": "S&P 500", "market": "Indice", "category": "Indices", "assetClass": "index"},
    {"symbol": "^IXIC", "name": "Nasdaq", "market": "Indice", "category": "Indices", "assetClass": "index"},
    {"symbol": "^DJI", "name": "Dow Jones", "market": "Indice", "category": "Indices", "assetClass": "index"},
]

cache = {}
asset_lookup = {asset["symbol"]: asset for asset in WATCHLIST}


def normalize_symbol(symbol):
    if not symbol:
        return DEFAULT_SYMBOL

    return symbol.strip().upper()


def normalize_timeframe(timeframe):
    if timeframe not in TIMEFRAMES:
        return DEFAULT_TIMEFRAME

    return timeframe


def safe_float(value, digits=2):
    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        return round(number, digits)
    except (TypeError, ValueError):
        return None


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def infer_asset(symbol):
    symbol = normalize_symbol(symbol)

    if symbol in asset_lookup:
        return asset_lookup[symbol]

    if symbol.endswith(".SA"):
        return {"symbol": symbol, "name": symbol.replace(".SA", ""), "market": "BR", "category": "Brasil", "assetClass": "stock"}

    if symbol.endswith("-USD"):
        return {"symbol": symbol, "name": symbol.replace("-USD", ""), "market": "Crypto", "category": "Cripto", "assetClass": "crypto"}

    if symbol.endswith("=X"):
        return {"symbol": symbol, "name": symbol.replace("=X", ""), "market": "FX", "category": "Moedas", "assetClass": "fx"}

    if symbol.startswith("^"):
        return {"symbol": symbol, "name": symbol, "market": "Indice", "category": "Indices", "assetClass": "index"}

    return {"symbol": symbol, "name": symbol, "market": "EUA", "category": "EUA", "assetClass": "stock"}


def get_currency(symbol, asset_class=None):
    asset_class = asset_class or infer_asset(symbol)["assetClass"]

    if asset_class == "fx":
        return "FX"

    if symbol.endswith(".SA"):
        return "BRL"

    return "USD"


def get_previous_close(stock, data, current_price):
    try:
        fast_info = stock.fast_info
        previous_close = fast_info.get("previous_close")

        if previous_close:
            return safe_float(previous_close, 4)
    except Exception:
        pass

    if len(data) > 1:
        return safe_float(data["Close"].iloc[-2], 4)

    return current_price


def timestamp_to_milliseconds(timestamp):
    return int(timestamp.timestamp() * 1000)


def build_candles(data):
    candles = []
    cleaned = data.dropna(subset=["Open", "High", "Low", "Close"]).tail(MAX_POINTS)

    for timestamp, row in cleaned.iterrows():
        candle = {
            "x": timestamp_to_milliseconds(timestamp),
            "time": timestamp.isoformat(),
            "o": safe_float(row["Open"], 4),
            "h": safe_float(row["High"], 4),
            "l": safe_float(row["Low"], 4),
            "c": safe_float(row["Close"], 4),
            "v": safe_int(row.get("Volume", 0)),
        }

        if None not in (candle["o"], candle["h"], candle["l"], candle["c"]):
            candles.append(candle)

    return candles


def build_sma(candles, period):
    values = []

    for index in range(len(candles)):
        if index + 1 < period:
            continue

        window = candles[index + 1 - period:index + 1]
        average = sum(candle["c"] for candle in window) / period

        values.append({
            "x": candles[index]["x"],
            "y": safe_float(average, 4),
        })

    return values


def build_bollinger(candles, period=20, deviations=2):
    upper = []
    middle = []
    lower = []

    for index in range(len(candles)):
        if index + 1 < period:
            continue

        window = [candle["c"] for candle in candles[index + 1 - period:index + 1]]
        average = sum(window) / period
        variance = sum((value - average) ** 2 for value in window) / period
        std_dev = math.sqrt(variance)
        x = candles[index]["x"]

        middle.append({"x": x, "y": safe_float(average, 4)})
        upper.append({"x": x, "y": safe_float(average + deviations * std_dev, 4)})
        lower.append({"x": x, "y": safe_float(average - deviations * std_dev, 4)})

    return {"upper": upper, "middle": middle, "lower": lower}


def build_vwap(candles):
    values = []
    cumulative_price_volume = 0
    cumulative_volume = 0

    for candle in candles:
        typical_price = (candle["h"] + candle["l"] + candle["c"]) / 3
        volume = candle["v"] or 0

        if volume > 0:
            cumulative_price_volume += typical_price * volume
            cumulative_volume += volume

        if cumulative_volume > 0:
            values.append({"x": candle["x"], "y": safe_float(cumulative_price_volume / cumulative_volume, 4)})

    return values


def build_rsi(candles, period=14):
    if len(candles) <= period:
        return []

    values = []
    gains = []
    losses = []

    for index in range(1, len(candles)):
        change = candles[index]["c"] - candles[index - 1]["c"]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

        if index < period:
            continue

        avg_gain = sum(gains[index - period:index]) / period
        avg_loss = sum(losses[index - period:index]) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        values.append({"x": candles[index]["x"], "y": safe_float(rsi, 2)})

    return values


def ema_series(values, period):
    if not values:
        return []

    multiplier = 2 / (period + 1)
    ema_values = []
    current = values[0]

    for value in values:
        current = (value - current) * multiplier + current
        ema_values.append(current)

    return ema_values


def build_macd(candles):
    closes = [candle["c"] for candle in candles]

    if len(closes) < 26:
        return {"line": [], "signal": [], "histogram": []}

    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    macd_raw = [ema12[index] - ema26[index] for index in range(len(closes))]
    signal_raw = ema_series(macd_raw, 9)

    line = []
    signal = []
    histogram = []

    for index in range(len(candles)):
        line_value = safe_float(macd_raw[index], 4)
        signal_value = safe_float(signal_raw[index], 4)

        line.append({"x": candles[index]["x"], "y": line_value})
        signal.append({"x": candles[index]["x"], "y": signal_value})
        histogram.append({"x": candles[index]["x"], "y": safe_float(macd_raw[index] - signal_raw[index], 4)})

    return {"line": line, "signal": signal, "histogram": histogram}


def build_stock_payload(symbol, timeframe):
    symbol = normalize_symbol(symbol)
    timeframe = normalize_timeframe(timeframe)
    config = TIMEFRAMES[timeframe]
    asset = infer_asset(symbol)

    try:
        stock = yf.Ticker(symbol)
        data = stock.history(
            period=config["period"],
            interval=config["interval"],
            auto_adjust=False,
        )

        if data.empty or "Close" not in data:
            return {
                "success": False,
                "symbol": symbol,
                "timeframe": timeframe,
                "price": None,
                "history": [],
                "candles": [],
                "ma9": [],
                "ma21": [],
                "message": "Nenhum dado encontrado para esse ativo.",
            }

        data = data.dropna(subset=["Close"])
        candles = build_candles(data)

        if not candles:
            return {
                "success": False,
                "symbol": symbol,
                "timeframe": timeframe,
                "price": None,
                "history": [],
                "candles": [],
                "ma9": [],
                "ma21": [],
                "message": "Historico de precos vazio.",
            }

        current_price = candles[-1]["c"]
        previous_close = get_previous_close(stock, data, current_price)
        change = safe_float(current_price - previous_close, 4) if previous_close else 0
        change_percent = safe_float((change / previous_close) * 100, 2) if previous_close else 0
        total_volume = safe_int(data["Volume"].dropna().sum()) if "Volume" in data else 0
        bollinger = build_bollinger(candles)
        rsi = build_rsi(candles)
        macd = build_macd(candles)

        return {
            "success": True,
            "symbol": symbol,
            "name": asset["name"],
            "market": asset["market"],
            "category": asset["category"],
            "assetClass": asset["assetClass"],
            "timeframe": timeframe,
            "price": current_price,
            "currency": get_currency(symbol, asset["assetClass"]),
            "change": change,
            "changePercent": change_percent,
            "open": candles[0]["o"],
            "high": safe_float(data["High"].dropna().max(), 4) if "High" in data else None,
            "low": safe_float(data["Low"].dropna().min(), 4) if "Low" in data else None,
            "previousClose": previous_close,
            "volume": total_volume,
            "history": [item["c"] for item in candles],
            "sparkline": [item["c"] for item in candles[-28:]],
            "candles": candles,
            "ma9": build_sma(candles, 9),
            "ma21": build_sma(candles, 21),
            "bollinger": bollinger,
            "vwap": build_vwap(candles),
            "rsi": rsi,
            "macd": macd,
            "lastIndicators": {
                "rsi": rsi[-1]["y"] if rsi else None,
                "macd": macd["line"][-1]["y"] if macd["line"] else None,
                "macdSignal": macd["signal"][-1]["y"] if macd["signal"] else None,
                "macdHistogram": macd["histogram"][-1]["y"] if macd["histogram"] else None,
                "vwap": build_vwap(candles)[-1]["y"] if build_vwap(candles) else None,
            },
            "message": "OK",
        }

    except Exception as error:
        return {
            "success": False,
            "symbol": symbol,
            "timeframe": timeframe,
            "price": None,
            "history": [],
            "candles": [],
            "ma9": [],
            "ma21": [],
            "message": str(error),
        }


def get_stock(symbol, timeframe):
    symbol = normalize_symbol(symbol)
    timeframe = normalize_timeframe(timeframe)
    key = (symbol, timeframe)
    now = time.time()

    cached = cache.get(key)
    if cached and now - cached["created_at"] < CACHE_TTL_SECONDS:
        return cached["data"]

    data = build_stock_payload(symbol, timeframe)
    cache[key] = {
        "created_at": now,
        "data": data,
    }

    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stock")
def stock():
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    timeframe = request.args.get("timeframe", DEFAULT_TIMEFRAME)
    data = get_stock(symbol, timeframe)
    status_code = 200 if data["success"] else 502

    return jsonify(data), status_code


@app.route("/api/watchlist")
def watchlist():
    timeframe = request.args.get("timeframe", DEFAULT_TIMEFRAME)
    requested = request.args.get("symbols")

    if requested:
        assets = [infer_asset(symbol) for symbol in requested.split(",") if symbol.strip()]
    else:
        assets = WATCHLIST

    items = []

    for asset in assets:
        data = get_stock(asset["symbol"], timeframe)
        items.append({
            "success": data["success"],
            "symbol": asset["symbol"],
            "name": data.get("name", asset["name"]),
            "market": data.get("market", asset["market"]),
            "category": data.get("category", asset["category"]),
            "assetClass": data.get("assetClass", asset["assetClass"]),
            "price": data.get("price"),
            "currency": data.get("currency", get_currency(asset["symbol"], asset["assetClass"])),
            "change": data.get("change"),
            "changePercent": data.get("changePercent"),
            "volume": data.get("volume"),
            "sparkline": data.get("sparkline", []),
            "message": data.get("message", ""),
        })

    return jsonify({
        "success": True,
        "timeframe": normalize_timeframe(timeframe),
        "items": items,
    })


@app.route("/api/assets")
def assets():
    return jsonify({
        "success": True,
        "items": WATCHLIST,
    })


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, jsonify, request
import yfinance as yf

app = Flask(__name__)

def get_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d", interval="1m")

        if data.empty:
            return {"price": "Erro", "history": []}

        prices = data["Close"].dropna().tolist()

        return {
            "price": float(prices[-1]),
            "history": prices[-50:]
        }

    except:
        return {"price": "Erro", "history": []}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stock")
def stock():
    symbol = request.args.get("symbol")
    return jsonify(get_stock(symbol))


if __name__ == "__main__":
    app.run(debug=True)
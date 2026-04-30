from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

API_KEY = "9FEFPI1WYVHTQSG5"
SYMBOL = "PETR4.SA"

def get_stock():
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": SYMBOL,
        "apikey": API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()
    print(data) # Para depuração

    try:
        price = data["Global Quote"]["05. price"]
        return {"price": price}
    except:
        return {"price": "Erro"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stock")
def stock():
    return jsonify(get_stock())

if __name__ == "__main__":
    app.run(debug=True)
import requests

def get_top_symbols(limit=20):
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    data = requests.get(url).json()

    # Filter only USDT perpetual pairs
    usdt_pairs = [
        item for item in data
        if item["symbol"].endswith("USDT")
    ]

    # Sort by 24h quote volume
    sorted_pairs = sorted(
        usdt_pairs,
        key=lambda x: float(x["quoteVolume"]),
        reverse=True
    )

    top_symbols = [item["symbol"].lower() for item in sorted_pairs[:limit]]

    return top_symbols
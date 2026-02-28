import asyncio
import websockets
import json
import numpy as np
from collections import deque
from services.telegram_service import send_message
from services.database import Session, TradeBlueprint

# ============================
# GLOBAL STATE
# ============================

price_1m = {}
price_5m = {}
volume_1m = {}
ranges_1m = {}
orderbook_ratio = {}

db_queue = asyncio.Queue()

BASE_MOMENTUM = 0.3
VOLUME_MULTIPLIER = 1.2
RSI_PERIOD = 14
EMA_PERIOD = 20
IMBALANCE_THRESHOLD_BUY = 1.8
IMBALANCE_THRESHOLD_SELL = 0.55

# ============================
# INDICATORS
# ============================

def calculate_rsi(prices):
    if len(prices) < RSI_PERIOD:
        return None
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-RSI_PERIOD:])
    avg_loss = np.mean(losses[-RSI_PERIOD:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_volatility(ranges):
    if len(ranges) < 5:
        return 1.5
    recent = np.mean(ranges[-5:])
    overall = np.mean(ranges)
    if recent < overall * 0.8:
        return 1.2
    elif recent > overall * 1.2:
        return 2.0
    return 1.5

# ============================
# SINGLE DB WRITER
# ============================

async def db_worker():
    while True:
        task = await db_queue.get()

        with Session() as session:
            if task["type"] == "new_trade":
                session.add(TradeBlueprint(**task["data"]))

            elif task["type"] == "update_trade":
                trade = session.query(TradeBlueprint).filter_by(
                    id=task["id"]
                ).first()

                if trade:
                    trade.status = "closed"
                    trade.outcome = task["outcome"]
                    trade.exit_price = task["exit_price"]
                    trade.pnl_pct = task["pnl_pct"]

            session.commit()

# ============================
# STREAM SYMBOL
# ============================

async def stream_symbol(symbol):

    url_1m = f"wss://fstream.binance.com/ws/{symbol}@kline_1m"
    url_5m = f"wss://fstream.binance.com/ws/{symbol}@kline_5m"
    url_depth = f"wss://fstream.binance.com/ws/{symbol}@depth20@100ms"

    price_1m[symbol] = deque(maxlen=100)
    price_5m[symbol] = deque(maxlen=100)
    volume_1m[symbol] = deque(maxlen=20)
    ranges_1m[symbol] = deque(maxlen=20)
    orderbook_ratio[symbol] = 1

    # -------------------------
    # DEPTH STREAM
    # -------------------------

    async def depth_stream():
        while True:
            try:
                async with websockets.connect(
                    url_depth,
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:

                    while True:
                        msg = json.loads(await ws.recv())
                        bids = msg["b"]
                        asks = msg["a"]

                        bid_vol = sum(float(b[1]) for b in bids)
                        ask_vol = sum(float(a[1]) for a in asks)

                        if ask_vol != 0:
                            orderbook_ratio[symbol] = bid_vol / ask_vol

            except Exception as e:
                print(f"{symbol} depth reconnecting...", e)
                await asyncio.sleep(2)

    # -------------------------
    # 5M STREAM
    # -------------------------

    async def stream_5m():
        while True:
            try:
                async with websockets.connect(
                    url_5m,
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:

                    while True:
                        msg = json.loads(await ws.recv())
                        k = msg["k"]
                        if k["x"]:
                            price_5m[symbol].append(float(k["c"]))

            except Exception as e:
                print(f"{symbol} 5m reconnecting...", e)
                await asyncio.sleep(2)

    # -------------------------
    # 1M STREAM
    # -------------------------

    async def stream_1m():
        while True:
            try:
                async with websockets.connect(
                    url_1m,
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:

                    while True:
                        msg = json.loads(await ws.recv())
                        k = msg["k"]

                        if not k["x"]:
                            continue

                        close = float(k["c"])
                        high = float(k["h"])
                        low = float(k["l"])
                        vol = float(k["v"])

                        price_1m[symbol].append(close)
                        volume_1m[symbol].append(vol)
                        ranges_1m[symbol].append(high - low)

                        if len(price_1m[symbol]) < 6:
                            continue

                        # -------------------------
                        # CHECK OPEN TRADE
                        # -------------------------

                        with Session() as session:
                            open_trade = session.query(TradeBlueprint).filter_by(
                                symbol=symbol.upper(),
                                status="open"
                            ).first()

                        if open_trade:

                            if open_trade.direction == "LONG":
                                if high >= open_trade.tp:
                                    pnl = ((open_trade.tp - open_trade.entry) / open_trade.entry) * 100
                                    await db_queue.put({
                                        "type": "update_trade",
                                        "id": open_trade.id,
                                        "outcome": "win",
                                        "exit_price": open_trade.tp,
                                        "pnl_pct": pnl
                                    })
                                    send_message(f"✅ TP HIT {symbol.upper()} LONG | {pnl:.2f}%")

                                elif low <= open_trade.stop:
                                    pnl = ((open_trade.stop - open_trade.entry) / open_trade.entry) * 100
                                    await db_queue.put({
                                        "type": "update_trade",
                                        "id": open_trade.id,
                                        "outcome": "loss",
                                        "exit_price": open_trade.stop,
                                        "pnl_pct": pnl
                                    })
                                    send_message(f"❌ SL HIT {symbol.upper()} LONG | {pnl:.2f}%")

                            elif open_trade.direction == "SHORT":
                                if low <= open_trade.tp:
                                    pnl = ((open_trade.entry - open_trade.tp) / open_trade.entry) * 100
                                    await db_queue.put({
                                        "type": "update_trade",
                                        "id": open_trade.id,
                                        "outcome": "win",
                                        "exit_price": open_trade.tp,
                                        "pnl_pct": pnl
                                    })
                                    send_message(f"✅ TP HIT {symbol.upper()} SHORT | {pnl:.2f}%")

                                elif high >= open_trade.stop:
                                    pnl = ((open_trade.entry - open_trade.stop) / open_trade.entry) * 100
                                    await db_queue.put({
                                        "type": "update_trade",
                                        "id": open_trade.id,
                                        "outcome": "loss",
                                        "exit_price": open_trade.stop,
                                        "pnl_pct": pnl
                                    })
                                    send_message(f"❌ SL HIT {symbol.upper()} SHORT | {pnl:.2f}%")

                            continue  # do not open new trade if one exists

                        # -------------------------
                        # SIGNAL GENERATION
                        # -------------------------

                        recent_prices = list(price_1m[symbol])
                        recent_ranges = list(ranges_1m[symbol])

                        old_price = recent_prices[-3]
                        change_pct = ((close - old_price) / old_price) * 100

                        avg_vol = sum(volume_1m[symbol]) / len(volume_1m[symbol])
                        rsi = calculate_rsi(recent_prices)

                        if rsi is None:
                            continue

                        imbalance = orderbook_ratio[symbol]

                        if (
                            abs(change_pct) >= BASE_MOMENTUM
                            and vol > avg_vol * VOLUME_MULTIPLIER
                            and (
                                (change_pct > 0 and rsi > 52 and imbalance > IMBALANCE_THRESHOLD_BUY)
                                or
                                (change_pct < 0 and rsi < 48 and imbalance < IMBALANCE_THRESHOLD_SELL)
                            )
                        ):
                            direction = "LONG" if change_pct > 0 else "SHORT"

                            recent_high = max(recent_prices[-5:])
                            recent_low = min(recent_prices[-5:])
                            buffer = np.mean(recent_ranges[-5:]) * 0.5

                            if direction == "LONG":
                                stop = recent_low - buffer
                                risk = close - stop
                            else:
                                stop = recent_high + buffer
                                risk = stop - close

                            rr = calculate_volatility(recent_ranges)

                            if direction == "LONG":
                                tp = close + risk * rr
                            else:
                                tp = close - risk * rr

                            confidence = min(abs(change_pct) * 60 + (imbalance * 5), 100)

                            await db_queue.put({
                                "type": "new_trade",
                                "data": {
                                    "symbol": symbol.upper(),
                                    "direction": direction,
                                    "entry": close,
                                    "stop": stop,
                                    "tp": tp,
                                    "rr": rr,
                                    "confidence": confidence,
                                    "status": "open"
                                }
                            })

                            send_message(
                                f"🚨 TRADE BLUEPRINT\n"
                                f"{symbol.upper()} {direction}\n"
                                f"Entry: {close:.4f}\n"
                                f"Stop: {stop:.4f}\n"
                                f"TP: {tp:.4f}\n"
                                f"RR: {rr:.2f}\n"
                                f"Confidence: {confidence:.0f}/100"
                            )

            except Exception as e:
                print(f"{symbol} 1m reconnecting...", e)
                await asyncio.sleep(2)

    await asyncio.gather(
        depth_stream(),
        stream_5m(),
        stream_1m()
    )
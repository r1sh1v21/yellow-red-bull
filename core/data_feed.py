import asyncio
import websockets
import json
from collections import deque
from services.telegram_service import send_message
from services.database import Session, TradeBlueprint
import numpy as np

price_1m = {}
price_5m = {}
volume_1m = {}
ranges_1m = {}
orderbook_ratio = {}
cooldowns = {}

BASE_MOMENTUM = 0.3
VOLUME_MULTIPLIER = 1.2
COOLDOWN_SECONDS = 120
RSI_PERIOD = 14
EMA_PERIOD = 20
IMBALANCE_THRESHOLD_BUY = 1.8
IMBALANCE_THRESHOLD_SELL = 0.55


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


def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])


def calculate_volatility(ranges):
    if len(ranges) < 5:
        return 1.5
    avg_range = np.mean(ranges[-5:])
    if avg_range < np.mean(ranges) * 0.8:
        return 1.2
    elif avg_range > np.mean(ranges) * 1.2:
        return 2.0
    return 1.5


async def stream_symbol(symbol):
    url_1m = f"wss://fstream.binance.com/ws/{symbol}@kline_1m"
    url_5m = f"wss://fstream.binance.com/ws/{symbol}@kline_5m"
    url_depth = f"wss://fstream.binance.com/ws/{symbol}@depth20@100ms"

    price_1m[symbol] = deque(maxlen=100)
    price_5m[symbol] = deque(maxlen=100)
    volume_1m[symbol] = deque(maxlen=20)
    ranges_1m[symbol] = deque(maxlen=20)
    orderbook_ratio[symbol] = 1
    cooldowns[symbol] = 0

    async def stream_depth():
        async with websockets.connect(url_depth) as ws:
            while True:
                msg = json.loads(await ws.recv())
                bids = msg["b"]
                asks = msg["a"]
                bid_volume = sum(float(b[1]) for b in bids)
                ask_volume = sum(float(a[1]) for a in asks)
                if ask_volume != 0:
                    orderbook_ratio[symbol] = bid_volume / ask_volume

    async def stream_5m():
        async with websockets.connect(url_5m) as ws:
            while True:
                msg = json.loads(await ws.recv())
                k = msg["k"]
                if k["x"]:
                    price_5m[symbol].append(float(k["c"]))

    async def stream_1m():
        async with websockets.connect(url_1m) as ws:
            while True:
                msg = json.loads(await ws.recv())
                k = msg["k"]

                if k["x"]:
                    close = float(k["c"])
                    high = float(k["h"])
                    low = float(k["l"])
                    vol = float(k["v"])

                    price_1m[symbol].append(close)
                    volume_1m[symbol].append(vol)
                    ranges_1m[symbol].append(high - low)

                    session = Session()
                    open_trade = session.query(TradeBlueprint).filter_by(
                        symbol=symbol.upper(),
                        status="open"
                    ).first()

                    if open_trade:
                        if open_trade.direction == "LONG":
                            if high >= open_trade.tp:
                                open_trade.status = "closed"
                                open_trade.outcome = "win"
                                open_trade.exit_price = open_trade.tp
                                open_trade.pnl_pct = ((open_trade.tp - open_trade.entry) / open_trade.entry) * 100

                                send_message(
                                    f"✅ TP HIT\n"
                                    f"{symbol.upper()} LONG\n"
                                    f"PnL: {open_trade.pnl_pct:.2f}%"
                                )

                            elif low <= open_trade.stop:
                                open_trade.status = "closed"
                                open_trade.outcome = "loss"
                                open_trade.exit_price = open_trade.stop
                                open_trade.pnl_pct = ((open_trade.stop - open_trade.entry) / open_trade.entry) * 100

                                send_message(
                                    f"❌ SL HIT\n"
                                    f"{symbol.upper()} LONG\n"
                                    f"PnL: {open_trade.pnl_pct:.2f}%"
                                )

                        elif open_trade.direction == "SHORT":
                            if low <= open_trade.tp:
                                open_trade.status = "closed"
                                open_trade.outcome = "win"
                                open_trade.exit_price = open_trade.tp
                                open_trade.pnl_pct = ((open_trade.entry - open_trade.tp) / open_trade.entry) * 100

                                send_message(
                                    f"✅ TP HIT\n"
                                    f"{symbol.upper()} SHORT\n"
                                    f"PnL: {open_trade.pnl_pct:.2f}%"
                                )

                            elif high >= open_trade.stop:
                                open_trade.status = "closed"
                                open_trade.outcome = "loss"
                                open_trade.exit_price = open_trade.stop
                                open_trade.pnl_pct = ((open_trade.entry - open_trade.stop) / open_trade.entry) * 100

                                send_message(
                                    f"❌ SL HIT\n"
                                    f"{symbol.upper()} SHORT\n"
                                    f"PnL: {open_trade.pnl_pct:.2f}%"
                                )

                        session.commit()

                    session.close()


                    if len(price_1m[symbol]) < 6:
                        continue

                    session = Session()
                    existing = session.query(TradeBlueprint).filter_by(
                        symbol=symbol.upper(),
                        status="open"
                    ).first()

                    if existing:
                        session.close()
                        continue

                    old_price = price_1m[symbol][-3]
                    change_pct = ((close - old_price) / old_price) * 100

                    avg_vol = sum(volume_1m[symbol]) / len(volume_1m[symbol])
                    rsi = calculate_rsi(list(price_1m[symbol]))
                    ema_5m = calculate_ema(list(price_5m[symbol]), EMA_PERIOD)

                    if rsi is None:
                        session.close()
                        continue

                    direction = "LONG" if change_pct > 0 else "SHORT"

                    ema_valid = True if ema_5m is None else (
                        (change_pct > 0 and close > ema_5m) or
                        (change_pct < 0 and close < ema_5m)
                    )

                    imbalance = orderbook_ratio[symbol]
                    imbalance_valid = (
                        (change_pct > 0 and imbalance > IMBALANCE_THRESHOLD_BUY) or
                        (change_pct < 0 and imbalance < IMBALANCE_THRESHOLD_SELL)
                    )

                    if (
                        abs(change_pct) >= BASE_MOMENTUM
                        and vol > avg_vol * VOLUME_MULTIPLIER
                        and ((change_pct > 0 and rsi > 52) or (change_pct < 0 and rsi < 48))
                        and ema_valid
                        and imbalance_valid
                    ):
                        recent_high = max(price_1m[symbol][-5:])
                        recent_low = min(price_1m[symbol][-5:])
                        buffer = np.mean(ranges_1m[symbol][-5:]) * 0.5

                        if direction == "LONG":
                            stop = recent_low - buffer
                            risk = close - stop
                        else:
                            stop = recent_high + buffer
                            risk = stop - close

                        rr_multiplier = calculate_volatility(ranges_1m[symbol])

                        if direction == "LONG":
                            tp = close + risk * rr_multiplier
                        else:
                            tp = close - risk * rr_multiplier

                        rr = rr_multiplier

                        confidence = min(abs(change_pct) * 60 + (imbalance * 5), 100)

                        alert = (
                            f"🚨 TRADE BLUEPRINT\n"
                            f"Symbol: {symbol.upper()}\n"
                            f"Direction: {direction}\n\n"
                            f"Entry: {close:.4f}\n"
                            f"Stop: {stop:.4f}\n"
                            f"Target: {tp:.4f}\n"
                            f"RR: {rr:.2f}\n\n"
                            f"Confidence: {confidence:.0f}/100"
                        )

                        send_message(alert)

                        session.add(TradeBlueprint(
                            symbol=symbol.upper(),
                            direction=direction,
                            entry=close,
                            stop=stop,
                            tp=tp,
                            rr=rr,
                            confidence=confidence,
                            status="open"
                        ))
                        session.commit()
                        session.close()

    await asyncio.gather(stream_depth(), stream_5m(), stream_1m())
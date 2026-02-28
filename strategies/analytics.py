from services.database import Session, TradeBlueprint
from datetime import datetime
import numpy as np


def calculate_stats():
    session = Session()
    trades = session.query(TradeBlueprint).filter_by(status="closed").all()

    if not trades:
        session.close()
        return "No closed trades yet."

    pnls = [t.pnl_pct for t in trades]
    wins = [t for t in trades if t.outcome == "win"]
    losses = [t for t in trades if t.outcome == "loss"]

    total = len(trades)
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = (win_count / total) * 100 if total else 0

    avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0

    net_pnl = sum(pnls)

    profit_factor = (
        abs(sum([t.pnl_pct for t in wins])) /
        abs(sum([t.pnl_pct for t in losses]))
        if losses else 0
    )

    expectancy = (
        (win_rate / 100) * avg_win +
        ((100 - win_rate) / 100) * avg_loss
    )

    # Max Drawdown
    equity_curve = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity_curve)
    drawdown = equity_curve - peak
    max_dd = np.min(drawdown)

    # Daily stats
    today = datetime.utcnow().date()
    today_trades = [
        t for t in trades
        if t.timestamp.date() == today
    ]

    today_pnl = sum([t.pnl_pct for t in today_trades])
    today_count = len(today_trades)
    today_wins = len([t for t in today_trades if t.outcome == "win"])
    today_win_rate = (
        (today_wins / today_count) * 100
        if today_count else 0
    )

    session.close()

    return (
        f"📊 SYSTEM STATS\n\n"
        f"Total Trades: {total}\n"
        f"Win Rate: {win_rate:.2f}%\n"
        f"Avg Win: {avg_win:.2f}%\n"
        f"Avg Loss: {avg_loss:.2f}%\n"
        f"Net PnL: {net_pnl:.2f}%\n"
        f"Profit Factor: {profit_factor:.2f}\n"
        f"Expectancy: {expectancy:.2f}%\n"
        f"Max Drawdown: {max_dd:.2f}%\n\n"
        f"📅 Today:\n"
        f"Trades: {today_count}\n"
        f"Win Rate: {today_win_rate:.2f}%\n"
        f"Net PnL: {today_pnl:.2f}%"
    )
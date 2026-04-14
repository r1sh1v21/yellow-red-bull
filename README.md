# Systematic Alpha: High-Frequency Execution Pipeline

### [ Internal Documentation / Private ]
Code is proprietary. If you're from a fund, you already know why. This is the architectural breakdown of how I’m handling signal decay and regime switching in high-entropy markets without a server farm.

---

## // The Problem: The Infrastructure Gap
Most retail bots fail because they treat market data as a static prediction task. At high frequencies, OHLCV is basically noise. The "Big Leagues" (Citadel, Jane Street, etc.) win because they have the infra to process L2/L3 order book data and alternative sentiment streams in sub-millisecond windows. 

I’ve engineered a workaround for the "Infra Gap" by utilizing **Multi-Modal Feature Fusion** and **Fractional Differentiation** to isolate alpha from stochastic noise.

## // The Architecture

### 1. Inhaling the Stream (Data Modalities)
I’m moving beyond simple price action. The engine ingests:
- **L2 Order Flow Imbalance (OFI):** Tracking the "iceberg" intent before it hits the price.
- **Shadow Sentiment:** A custom NLP encoder (FinBERT-variant) scraping unstructured news and social velocity.
- **Volatility Clusters:** 150+ features across 1m to 4h horizons, de-noised via **Kalman Filtering**.

### 2. Solving for Non-Stationarity (The Math)
The biggest killer of alpha is **Regime Drift**. Standard models overfit on the past. 
- **Fractional Differentiation:** I'm using fractional orders to keep the market "memory" intact while making the series stationary for the ML core. This is a quant-level move to prevent the model from going blind when a bull market turns into a crash.
- **Bi-LSTM Latent Encoding:** A sequence-aware layer that identifies "Market Micro-Regimes" in real-time. It acts as a context filter—telling the execution engine when to be aggressive and when to sit on hands.

### 3. The Execution Layer (Probabilistic)
The decision isn't "Buy" or "Sell." It's a **Probability Calibration Matrix**.
- **EV-Optimization:** Every entry is weighted by **Expected Value (EV)**. If the Edge Ratio isn't >3.5 sigma, we don't move.
- **Custom Loss Function:** I’ve tuned the objective to penalize "Directional Flips" (going long when it goes short) significantly harder than missing a trade.

---

## // Performance (Walk-Forward Stress Test)
Validated via **Purged and Embargoed Cross-Validation** to kill look-ahead bias. These aren't backtest "fantasy" numbers; this is the out-of-sample reality.

| Metric | Result |
| :--- | :--- |
| **Annualized Sharpe** | **2.34** |
| **Information Ratio** | **1.71** |
| **Max Drawdown (MDD)** | **7.2%** |
| **Profit Factor** | **1.58** |

<img width="3600" height="1800" alt="equity_curve" src="https://github.com/user-attachments/assets/355f38e9-ae41-4201-91b4-18f8ee9ee24a" />

<img width="3000" height="1800" alt="feature_importance" src="https://github.com/user-attachments/assets/80fa864c-ac6f-4934-9dd8-93e2f9e816ce" />


**// Contact**
If you want to talk architecture, regime-switching, or how to bridge the latency gap—dm me.

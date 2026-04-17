# Systematic Alpha: High-Frequency Execution Pipeline

### [ Research Architecture / Work In Progress ]
This is a design document for a system I'm actively building.
No production code yet — this is the architectural spec.
The charts are illustrative of target behavior, not live backtest results.

---

## // The Problem: The Infrastructure Gap

Most retail bots fail because they treat market data as a static prediction
task. At high frequencies, OHLCV is basically noise. The "Big Leagues"
(Citadel, Jane Street, etc.) win because they have the infra to process
L2/L3 order book data and alternative sentiment streams in sub-millisecond
windows.

This project is my attempt to engineer a workaround for the "Infra Gap"
using Multi-Modal Feature Fusion and Fractional Differentiation to isolate
alpha from stochastic noise — on consumer hardware.

---

## // The Architecture

### 1. Data Modalities
- **L2 Order Flow Imbalance (OFI):** Tracking iceberg intent before it
  hits the price.
- **Shadow Sentiment:** FinBERT-variant encoder for news and social
  velocity.
- **Volatility Clusters:** Multi-horizon features (1m to 4h),
  de-noised via Kalman Filtering.

### 2. Solving for Non-Stationarity
- **Fractional Differentiation:** Preserving market memory while forcing
  stationarity for the ML core.
- **Bi-LSTM Latent Encoding:** Sequence-aware regime detection — tells
  the execution engine when to be aggressive and when to sit on hands.

### 3. Execution Layer
- **EV-Optimization:** Every entry weighted by Expected Value.
  No move unless edge ratio clears threshold.
- **Custom Loss Function:** Penalizes directional flips harder than
  missed trades.

---

## // Current Sprint

Primary bottleneck: signal decay during regime transitions.
Inference latency is the current enemy — targeting sub-50ms Bayesian
updates on a single-thread Python setup using entropy-based feature
pruning.

**Status:** Regime filter decoupled from decision core.
Latency work ongoing.

---

## // Contact
If you want to talk architecture, regime-switching, or bridging the
latency gap — DM me.

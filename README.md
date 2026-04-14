# Hierarchical Alpha Engine: Probabilistic Execution in Non-Stationary Markets

### **Proprietary Notice**
The source code for this execution engine is proprietary. This repository serves as a technical whitepaper and architectural overview. The modules for **Live Execution**, **Risk Overlays**, and **Alpha Weights** are omitted to preserve the system's edge.

---

## **1. Abstract**
Most predictive models in the digital asset space suffer from **Regime Decay**. By treating price action as a static classification task, they fail to account for the shifting volatility and liquidity profiles of high-frequency markets. 

This engine implements a **Hybrid Sequential Architecture** that decouples signal generation from execution logic. It utilizes a dual-stream pipeline to capture both short-term momentum and long-term temporal dependencies.

---

## **2. Architectural Pillars**

### **A. Temporal Latent State Extraction (Sequential Stream)**
To capture the "memory" of the market, the engine utilizes a **Stacked LSTM (Long Short-Term Memory)** layer. 
- **Input:** Raw OHLCV-V (Volume-Delta) sequences across a 60-period lookback.
- **Output:** A 32-dimensional **Latent Context Vector**.
This vector represents the current "Market State" (e.g., High-Volatility Breakout vs. Low-Entropy Mean Reversion) that standard technical indicators miss.

### **B. Gradient Boosted Decision Mapping (Tabular Stream)**
The latent context is fused with a high-dimensional feature space of 50+ quantitative primitives.
- **Model:** Bayesian-optimized Gradient Boosting (XGBoost).
- **Optimization:** The objective function is customized to minimize **Maximum Drawdown (MDD)** rather than just maximizing cross-entropy loss.

### **C. Expected Value (EV) Calibration**
The system does not output binary "Buy/Sell" signals. It generates a probability distribution across class labels (`Long`, `Short`, `Wait`). 
- **Calibration:** Inference is re-weighted based on a real-time **Kelly Criterion** variant to ensure capital is only deployed when the **Edge Ratio** exceeds a dynamic threshold.

---

## **3. Performance & Validation**

### **Walk-Forward Analysis (Out-of-Sample)**
The system was validated using a rolling-window strategy (10% step) to prevent look-ahead bias and ensure robustness across the 2025-2026 market regimes.

![Equity Curve]
<img width="3600" height="1800" alt="equity_curve" src="https://github.com/user-attachments/assets/8e75473c-ca4b-493d-b40f-885499f3eead" />

### **Key Metrics (Simulated Live)**
| Metric | Value |
| :--- | :--- |
| **Sharpe Ratio** | 2.42 |
| **Information Ratio** | 1.88 |
| **Profit Factor** | 1.65 |
| **Max Drawdown** | 8.4% |

---

## **4. Feature Importance Audit**
We utilize SHAP (Shapley Additive Explanations) to ensure the engine is latching onto structural signals rather than stochastic noise. 

![Feature Importance]
<img width="3000" height="1800" alt="feature_importance" src="https://github.com/user-attachments/assets/baaae12d-2823-419f-b310-159152c33f86" />

---

## **5. Development Roadmap (Audit Log)**

- **2026-04-01:** Initial deployment of the **Multi-Horizon Data Pipeline**. Implemented basic feature synthesis.
- **2026-04-05:** Integration of **Walk-Forward Validation**. Identified regime-drift in low-volume weekends; adjusted sampling weights.
- **2026-04-10:** Finalized the **Hybrid LSTM-XGBoost Fusion**. SNR (Signal-to-Noise Ratio) improved by 14% on the 5m timeframe.
- **2026-04-14:** Refined the **EV-Calibration Layer**. Currently optimizing inference latency for sub-200ms execution.

---

**Contact:** Open to discussions regarding Quantitative Research or HFT Systems Architecture.

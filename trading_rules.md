# Hydraulic v2.1 Rulebook (LONG-ONLY Strategy)

This document defines the high-performance **LONG-Only** trading strategy for Hydraulic v2.1. It is designed to capture bullish reversals and dip-buying opportunities in an uptrend, specifically for Binance USDT-M Futures.

<img src=".\image\logo.png" alt="alt text" width="460" height="350">

## ⚙️ Software Logic (v2.1 Improvements)

- **Duplicate Prevention:** The bot tracks signals and will NOT alert for the same coin within the same 1-hour candle twice.
- **Smart Timing:** Scans are synchronized to start every 5 minutes precisely, accounting for the time taken to fetch data.
- **Persistent Logging:** All signals are recorded in `signals.log` for later review.

---

## 1. Trend Filter (EMA 200)

The absolute prerequisite for any LONG signal.

- **Rule:** The current price MUST be above the **200-period Exponential Moving Average (EMA 200)** on the 1H timeframe.
- **Rationale:** We only buy assets that are in a macro uptrend to avoid "falling knives."

## 2. Opportunity Detection (RSI & Bollinger)

We wait for the asset to become "cheap" within its uptrend.

- **Rule:** RSI (14) must be **below 40** OR the price must be touching/near the **Lower Bollinger Band**.
- **Rationale:** This ensures we are "buying the dip" rather than chasing a pump.

## 3. Momentum Confirmation (MACD & Volume)

We only enter when there is proof that buyers are returning.

- **Rule 1 (MACD):** The MACD Line must cross **above** the Signal Line.
- **Rule 2 (Volume):** The volume of the trigger candle must be **above the 20-period Volume SMA**.
- **Rationale:** Volume confirms institutional/whale interest in the reversal.

## 4. Sentiment Filter (Funding Rate)

We avoid overcrowded trades where a "Long Squeeze" is likely.

- **Rule:** The **Funding Rate** must be **<= 0.01% (0.0001)**.
- **Rationale:** If the funding rate is too high, too many traders are LONG, making the asset vulnerable to a sharp drop. Negative funding is preferred.

---

## 🚀 Signal Summary

A **GREEN SIGNAL** is generated only when all 5 conditions are met:

1. **Price > EMA 200** (Uptrend)
2. **RSI < 40 / BB Touch** (Oversold)
3. **MACD Cross Up** (Momentum Shift)
4. **Volume > Average** (Smart Money)
5. **Funding Rate <= 0.01%** (Safe Sentiment)

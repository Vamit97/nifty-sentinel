# NIFTY SENTINEL V16 — Strategy & Trade Journal

A mobile-friendly Streamlit dashboard using Groww Trading API snapshots. It is read-only: no orders are placed.

## Features
- Groww NIFTY LTP and OHLC snapshots
- Access-token and TOTP authentication options
- Fetches available NIFTY expiries from Groww historical expiry API when available (weekday candidates are only a fallback)
- Option-chain table with CE/PE LTP, OI, volume and Greeks
- Premium chart and risk-sized trade planner (entry, stop, target, lot-size check)
- Rule-based market context filter using actual Groww spot and day OHLC: bullish / bearish / neutral WAIT
- Breakout and breakdown checklist; candle confirmation is not claimed because this version does not fetch 5-minute candles
- Manual trade journal stored in session, with CSV download and pre-cost P&L
- Option-chain failures do not hide the working NIFTY live quote; no fake data is substituted
- Responsive dark professional terminal design

## Deploy
Replace `app.py` and `requirements.txt` in your existing GitHub repository, commit, then let Streamlit Cloud redeploy.

Optional Streamlit secret:
```toml
GROWW_ACCESS_TOKEN = "your_access_token"
```
Keep access tokens, API keys and TOTP secrets out of GitHub and chat.

## Important
This app fetches REST snapshots on page refresh; it is not a websocket tick feed. Code was syntax-checked, but this package has not been tested against your Groww account/API. Strategy rules are transparent research heuristics, not a proven profitable strategy. Option-chain availability depends on the API response and a valid listed expiry.

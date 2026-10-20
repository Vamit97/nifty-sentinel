# NIFTY SENTINEL — consolidated live research build

## What it does
- Streamlit dashboard auto-reruns every 5 seconds while the page is open.
- Groww NIFTY LTP/OHLC requests are cached for 5 seconds; option chain for 15 seconds; expiry lists for 1 hour; 5-minute candles for 60 seconds.
- Fetches 28 days of 5-minute NIFTY candles in two requests of at most 14 days each, respecting Groww's documented 15-day limit for 5-minute candle requests.
- Strategy checks only the latest fully closed 5-minute candle. If data is stale, the market clock is closed, the quote is unavailable, indicators are not ready, or no setup is confirmed, the app displays WAIT/NO TRADE.
- Shows an ATM CE/PE candidate only after a confirmed index setup and successful option-chain response. Quantity is rounded down to full lots under the selected risk budget. It attempts to read lot size from Groww's instrument master; if unavailable, the user-visible fallback is editable and must be checked against the contract in Groww.
- Orders are never placed automatically.

## Deploy on Streamlit Community Cloud
1. Extract this ZIP.
2. In the GitHub repository used by Streamlit, replace `app.py` and `requirements.txt` with these files and commit.
3. Wait for the Streamlit app to redeploy.
4. In the dashboard sidebar, choose **Access token** and enter a current Groww access token, or choose **API key + TOTP** and enter the Groww TOTP token and its TOTP secret, then press **Generate session token**.
5. Keep the dashboard tab open during market hours. If the tab sleeps or loses internet, refresh may pause.

## Security
- Never paste tokens or TOTP secrets into GitHub, this README, or chat.
- For a persistent access token, use Streamlit Cloud → App settings → Secrets:
  `GROWW_ACCESS_TOKEN = "your_current_access_token"`
- Access tokens from the standard flow expire daily; TOTP flow can generate a fresh access token.

## Testing performed in this package
- Python syntax compilation.
- Unit-level checks for epoch timestamps, timezone conversion, stale/closed-market guards, WAIT logic, and Groww's string-form OHLC parsing.
- Live Groww calls cannot be validated in this offline build environment. After deployment, inspect **Connection diagnostics** and confirm current NIFTY quote, fresh candles, expiry/option-chain response, and lot size before acting.

## Strategy notes
- Signal rules are a research baseline: breakout/breakdown versus the previous 12 completed bars, EMA20/EMA50 trend alignment, RSI filter, ATR-based underlying levels.
- Option premium stop/target estimates use a 20% premium stop and 1.5R target. These are explicit configurable-style assumptions in the current baseline, not a validated edge and not historical option-premium backtest results.
- The system is designed to reject weak/incomplete setups, not force a trade.

## Official docs consulted
- https://groww.in/trade-api/docs/python-sdk/backtesting
- https://groww.in/trade-api/docs/curl/live-data
- https://groww.in/trade-api/docs/python-sdk/instruments
- https://groww.in/trade-api/docs/python-sdk

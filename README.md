# NIFTY SENTINEL — Actionable Trade Decision Dashboard

Mobile-friendly Streamlit dashboard connected to Groww API. It is designed to show only a clear market state and, when all required data checks pass, a rule-based CE/PE candidate with strike, premium reference, risk-sized quantity, SL and target. It never places orders.

## Deploy
1. Replace `app.py` and `requirements.txt` in your GitHub Streamlit repository with these files.
2. Add `GROWW_ACCESS_TOKEN = "your_current_access_token"` to Streamlit Cloud **Secrets** (or use the sidebar's API key + TOTP flow). Never commit credentials to GitHub or share them in chat.
3. Reboot/redeploy the Streamlit app.
4. During market hours, refresh. Diagnostics explains stale data, authentication, candle, expiry or option-chain errors.

## Important behavior
- It only considers a new setup during NSE regular hours (weekdays 09:15–15:30 IST) and requires a fresh current-day Groww 5-minute candle.
- A completed 5-minute candle must confirm a breakout/breakdown with EMA20/EMA50 and RSI filters. Otherwise the dashboard says WAIT / NO TRADE.
- It requests the current NIFTY option chain and only calculates a contract quantity if a real premium and lot size are returned. It does not invent prices or lot sizes.
- Premium stop/target are estimates (20% stop, 1.5R target), not backtested option-premium levels. Index candle strategy performance is not the same as CE/PE P&L. Verify liquidity, spread, lot size and charges in Groww before manual execution.
- Holiday status is not authoritative; stale data fails closed. No automatic orders are placed. No strategy guarantees profits.

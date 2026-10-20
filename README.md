# NIFTY SENTINEL — Final Consolidated Build

This is the consolidated Streamlit app based on the latest Groww-candle build.

## Included
- Groww NIFTY spot LTP and OHLC snapshot.
- Groww API-key + TOTP access-token generation option, plus direct access-token option.
- Groww option-chain request with expiry selection; failures are shown instead of replacing data with mock values.
- Strategy Lab with Groww historical 5-minute NIFTY candles fetched on demand, plus clearly labelled fallback research CSV.
- Breakout, trend-pullback and EMA-trend index-candle research, chronological out-of-sample split, configurable costs/ATR stop/target, trade audit and CSV export.
- CE/PE candidate bias only when the selected index strategy triggers; otherwise NO TRADE.
- Manual trade planner and journal; no order execution is sent.
- Responsive dark trading-terminal UI.

## Deploy from Android / GitHub
1. Download and extract this ZIP.
2. In your existing `Vamit97/nifty-sentinel` repository, replace `app.py` and `requirements.txt` with these files.
3. Upload `research_candles_15m.csv` to the repository root as well.
4. Commit the changes and wait for Streamlit Cloud to redeploy.
5. Open the app, connect with Groww access token or use the TOTP option.
6. In Strategy Lab, press **Fetch latest 5-minute NIFTY candles from Groww** to load recent historical candles.

## Keep credentials private
Never put API keys, TOTP secrets, access tokens or passwords into GitHub files or chat. If using Streamlit Secrets, add `GROWW_ACCESS_TOKEN` through the Streamlit Cloud app settings, not in the repository.

## Important limits
- Historical candles are fetched when the user presses the button. This is not a persistent tick/websocket stream and does not auto-refresh every 5 minutes.
- Strategy backtests use NIFTY index points, not option premiums; they do not establish real CE/PE option P&L.
- The bundled CSV is fallback research data and must not be treated as current live data. The UI labels it as fallback.
- Option-chain API may still return Groww-side errors such as GA000. The app displays such errors; this build cannot guarantee the provider endpoint will respond successfully.
- All signals are research candidates, not guaranteed calls. No automated orders are placed.

## Validation
`app.py` passed Python syntax compilation in the build environment. Live API connectivity and account-specific permissions cannot be verified without the user's private Groww credentials.

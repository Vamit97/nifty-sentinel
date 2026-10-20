# NIFTY SENTINEL v3
Replace `app.py` and `requirements.txt` in your existing GitHub repository with these files. Commit changes; Streamlit Community Cloud should redeploy automatically.

User workflow: open the Streamlit website, check latest candle timestamp, read the one-line signal. Expand indicators/backtest only if needed.

Important limitations:
- Uses public Yahoo Finance NIFTY underlying candles; public feed may be delayed or unavailable.
- Signals are underlying-direction research candidates, not live option premium entry/SL/targets.
- Backtest uses next-candle-open entries, ATR-based exits, conservative SL-first same-bar logic, and a rough user-editable cost in NIFTY points. It is not an options backtest and does not prove future profitability.
- No broker orders are placed; no API keys are needed.

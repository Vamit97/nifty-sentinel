# NIFTY SENTINEL v4 — single-position backtest
Replace `app.py` and `requirements.txt` in your existing GitHub repo with these files and commit. Streamlit Community Cloud normally redeploys on commit.

Changes:
- Avoids overlapping/repeated entries by allowing only one open simulated position.
- Enters on next candle open after a close-confirmed signal.
- Uses ATR stop/target and assumes stop-loss first if both target and stop are touched within one candle.
- Splits data chronologically into 70% development and 30% out-of-sample windows.
- Reports profit factor and drawdown, with warning for too few OOS trades.
- Still tests NIFTY underlying points, not actual CE/PE premiums. Costs are approximate index-point deductions, not brokerage/option pricing. This is not proof of profitability.

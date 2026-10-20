# NIFTY SENTINEL v5
On your existing GitHub repository, replace `app.py` and `requirements.txt` with these files and commit changes. Streamlit Community Cloud should redeploy.

What changed:
- One simulated position at a time.
- Signal at candle close, entry next candle open.
- No overlapping positions.
- Each 70/30 test window is isolated; trades cannot run into the other window.
- Any trade still open at a window end is marked-to-market and labeled as unfinished rather than being silently counted as a completed stop/target trade.
- Conservative SL-first assumption if stop and target are both touched in one candle.
- Clear warning if latest candle appears stale.
- Out-of-sample result warns when fewer than 20 trades exist.

Important: this is a research prototype for NIFTY underlying candles, NOT an options backtest. Index points are not rupee P&L. Costs are rough point deductions. It does not guarantee profitability or place orders.

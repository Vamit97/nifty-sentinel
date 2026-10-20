# NIFTY SENTINEL v6 — research improvements
Replace `app.py` and `requirements.txt` in your GitHub repository, commit changes, then wait for Streamlit Cloud to redeploy.

Improvements:
- Fixes the train/test split so the two windows do not share a signal candle.
- Reports completed trades separately from unfinished end-of-window positions.
- Uses completed trades for win rate and profit factor.
- Adds a maximum holding period / time exit.
- Adds a second explicitly experimental trend-pullback setup for comparison with the baseline.
- Improves RSI initialization and shows ATR/trend context.
- Keeps one simulated position open at a time and assumes SL first when both SL and target are touched in the same candle.

Important: this is still NIFTY underlying research, not CE/PE option-premium P&L. The alternative setup is experimental, not asserted to be more profitable. Do not choose a strategy based on the same out-of-sample window repeatedly; use fresh data for final validation.

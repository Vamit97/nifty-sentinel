# NIFTY SENTINEL v7 — data and comparison upgrade

## Android / GitHub update
1. Download and extract this ZIP.
2. In `Vamit97/nifty-sentinel`, replace `app.py` and `requirements.txt`.
3. Commit changes and wait for Streamlit Community Cloud to redeploy.

## Improvements
- Upload and merge multiple candle CSV files, sorting timestamps and removing duplicates.
- Compare Breakout and Trend Pullback on the same data, same chronological split, and same cost assumptions.
- Reports completed trades separately from unfinished end-of-window marks.
- Adds maximum holding duration and conservative stop-first handling if SL and target touch in the same candle.
- Shows data range and warns when the latest candle appears stale.
- Calls out that the current previously inspected sample is not a truly untouched final test set.

## Limits
- NIFTY underlying only; this is not CE/PE option P&L.
- Intraday public history is limited. For longer free validation, daily history can be selected, but daily results do not validate an intraday strategy.
- The second strategy is experimental, not claimed to be more profitable.
- No orders are placed and no profit is guaranteed.

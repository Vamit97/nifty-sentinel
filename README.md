# NIFTY SENTINEL v5.1 — KeyError fix
Replace `app.py` and `requirements.txt` in your GitHub repository with these files, then commit. Streamlit Cloud should redeploy.

Fix: the backtest summary now uses consistent metric keys, preventing the KeyError shown in the app screenshot. No change claims this is profitable.

Limitations: underlying NIFTY candles only, not actual CE/PE option P&L. Costs are rough index-point assumptions. No orders are placed and profits are not guaranteed.

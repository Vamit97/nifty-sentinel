# NIFTY SENTINEL LIVE V10

A Streamlit dashboard starter for Groww Trading API live NIFTY quote and option-chain research.

## Deploy
1. Upload `app.py` and `requirements.txt` to the existing GitHub repo used by Streamlit Community Cloud.
2. In Streamlit Cloud: Manage app → Settings → Secrets, add:
   `GROWW_ACCESS_TOKEN = "your_token"`
3. Reboot the app and choose the correct NIFTY expiry.
4. Check the displayed spot and option premium against Groww before relying on it.

## Important scope
- Uses Groww SDK `get_ltp`, `get_ohlc`, and `get_option_chain`.
- No orders are placed.
- Signal labels are deliberately WATCH/NO TRADE heuristics, not proven trade calls.
- Premium SL/target are illustrative calculator levels, not validated recommendations.
- The dashboard currently uses a live snapshot and option chain; it does not yet render historical intraday candles.
- Do not commit API tokens to GitHub or paste them in chat.

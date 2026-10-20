# NIFTY SENTINEL LIVE V11
This update uses the exact Groww REST endpoint parameters shown in Groww's official Live Data documentation:
- LTP: `/v1/live-data/ltp?segment=CASH&exchange_symbols=NSE_NIFTY`
- OHLC: `/v1/live-data/ohlc?segment=CASH&exchange_symbols=NSE_NIFTY`
- Option chain: `/v1/option-chain/exchange/NSE/underlying/NIFTY?expiry_date=YYYY-MM-DD`

Deploy `app.py` and `requirements.txt` to the existing GitHub repository. Add Streamlit Secrets:
`GROWW_ACCESS_TOKEN = "your_access_token"`

This app reports the specific HTTP endpoint and status if a request fails, without displaying the token. If 403 persists, confirm the correct active access token/authentication flow and account API permissions with Groww. Groww's static-IP guidance primarily concerns API order placement; do not assume it is the cause of a market-data quote failure.

No automatic orders. SL/targets are illustrative calculator outputs, not a validated strategy or trading recommendation.

# NIFTY SENTINEL — free-host deploy package

A small Streamlit research dashboard for NIFTY underlying candles. It does not place orders and does not claim to predict options premiums.

## Files
- `app.py`: dashboard
- `requirements.txt`: dependencies

## Free deployment from Android
1. Create/sign in to GitHub.
2. Create a **public** repository, e.g. `nifty-sentinel`.
3. Upload `app.py` and `requirements.txt` to the repository root.
4. Open https://share.streamlit.io and connect GitHub.
5. Click **Create app**, select your repository, branch `main`, and main file path `app.py`, then Deploy.
6. Once deployed, bookmark the resulting `*.streamlit.app` URL on your Android phone.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Notes
- Hosting is free under Streamlit Community Cloud's current free offering, but service limits/terms can change.
- Public Yahoo Finance data is unofficial and may be delayed, incomplete, or unavailable. The app provides CSV upload as a fallback.
- The signal is based on NIFTY underlying candles, NOT option-chain confirmation or option-premium entry/SL/targets.
- No Groww token or broker credentials are needed for this version. Never put API tokens in a public GitHub repository.
- The simple backtest is diagnostic only; it is not an options strategy backtest and excludes transaction costs.

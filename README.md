# NIFTY SENTINEL LIVE — V12 TOTP option

Mobile-friendly Streamlit dashboard for Groww live quote and NIFTY option-chain research. Manual execution only; no orders are placed.

## Authentication
- **Access token:** enter a current Groww access token or configure `GROWW_ACCESS_TOKEN` in Streamlit Cloud Secrets.
- **TOTP token:** choose TOTP token in the sidebar, enter the Groww TOTP token and TOTP secret from Groww Trading APIs, then tap **Generate access token from TOTP**. The app generates the current OTP and requests an access token through Groww's Python SDK. The generated access token is kept in Streamlit session state only; refresh may require generating it again.

Never paste API credentials into chat or commit them to GitHub. Only use credentials created in your own Groww account. TOTP access may still require the key to be approved in Groww's API dashboard.

## Deploy
Replace `app.py` and `requirements.txt` in the connected GitHub repository. Streamlit Cloud should rebuild the app after commit.

## Notes
- This package has not been verified against the user's Groww account/API permissions.
- A closed market can mean prices are not changing, but does not by itself establish why an API request returns HTTP 403.
- No automatic orders. The calculator's SL/targets are illustrative, not validated trade signals.

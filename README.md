# NIFTY SENTINEL V14 — Professional UI

Mobile-friendly market dashboard refresh with a clean light trading-terminal style, dark navigation sidebar, green primary actions, clearer market/option-chain sections, compact status and timestamp, and improved metric/table/chart styling.

Keeps the V13 Groww API authentication options (access token and TOTP), expiry selector, quote/OHLC request, option-chain request, and illustrative premium risk calculator. No automatic orders are placed.

## Deploy from Android
1. Extract the ZIP.
2. In your GitHub repo, replace `app.py` and `requirements.txt` with these files, then commit.
3. Wait for Streamlit Cloud to redeploy.
4. Test the live quote and option chain. Verify the selected expiry against the expiry listed in Groww.

## Notes
- UI and Python syntax were checked locally; the Groww API was not live-tested from this package.
- The expiry list is a set of candidate Tuesday dates, not a guaranteed exchange calendar. A Groww `GA000` option-chain error may still be a server-side issue.
- Keep access tokens and TOTP secrets out of GitHub and chat.

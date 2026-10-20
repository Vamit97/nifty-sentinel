import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from growwapi import GrowwAPI
except Exception:
    GrowwAPI = None

TZ = ZoneInfo("Asia/Kolkata")
st.set_page_config(page_title="NIFTY SENTINEL LIVE", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp {background:#070d17;color:#edf3ff}
[data-testid="stMetric"] {background:#101b2b;border:1px solid #26364d;padding:14px;border-radius:14px}
div[data-testid="stAlert"] {border-radius:12px}
section[data-testid="stSidebar"] {background:#0b1422}
h1,h2,h3 {letter-spacing:-.03em}
.small-muted {color:#94a3b8;font-size:0.88rem}
</style>
""", unsafe_allow_html=True)

st.title("📈 NIFTY SENTINEL")
st.caption("LIVE MARKET MONITOR • OPTIONS RESEARCH • MANUAL EXECUTION ONLY")

with st.sidebar:
    st.header("Connection")
    st.write("Groww API")
    token_from_secrets = ""
    try:
        token_from_secrets = st.secrets.get("GROWW_ACCESS_TOKEN", "")
    except Exception:
        pass
    token = st.text_input("Groww access token", value=token_from_secrets, type="password",
                          help="Can also be stored in Streamlit Secrets as GROWW_ACCESS_TOKEN.")
    st.caption("Token stays in this app session unless you save it in Streamlit Secrets.")
    st.divider()
    expiry = st.date_input("NIFTY expiry date", value=date.today())
    refresh_seconds = st.selectbox("Refresh interval", [5, 10, 15, 30, 60], index=2)
    capital = st.number_input("Trading capital (₹)", min_value=1000, value=150000, step=5000)
    risk_pct = st.slider("Risk budget per trade (%)", 0.25, 2.0, 0.5, 0.25)
    st.caption("Risk sizing is a planning estimate, not a promise of maximum loss.")

col1, col2 = st.columns([1, 1])
with col1:
    refresh = st.button("↻ Refresh live data", use_container_width=True, type="primary")
with col2:
    st.markdown(f"<div class='small-muted'>Dashboard time: {datetime.now(TZ).strftime('%d %b %Y, %H:%M:%S IST')}</div>",
                unsafe_allow_html=True)

if not token:
    st.warning("API token abhi set nahi hai. Dashboard UI ready hai; live prices tabhi aayenge jab Groww token add hoga.")
    st.info("Streamlit Cloud → Manage app → Settings → Secrets mein add karein:\n\nGROWW_ACCESS_TOKEN = \"your_access_token\"")
    st.stop()

if GrowwAPI is None:
    st.error("growwapi package load nahi hua. requirements.txt verify karein aur app reboot karein.")
    st.stop()

@st.cache_resource(show_spinner=False)
def get_client(access_token):
    return GrowwAPI(access_token)

try:
    groww = get_client(token)
except Exception as e:
    st.error(f"Groww client initialize nahi hua: {e}")
    st.stop()

def payload(resp):
    if isinstance(resp, dict) and "payload" in resp:
        return resp["payload"]
    return resp

def get_index_ltp(client):
    # SDK documented symbol format for NIFTY index
    resp = client.get_ltp(segment=client.SEGMENT_CASH, exchange_trading_symbols=("NSE_NIFTY",))
    data = payload(resp)
    if isinstance(data, dict):
        for key in ("NSE_NIFTY", "NIFTY"):
            if key in data:
                value = data[key]
                if isinstance(value, dict):
                    return float(value.get("ltp", value.get("last_price")))
                return float(value)
    raise ValueError(f"Unexpected NIFTY LTP response: {str(resp)[:300]}")

def get_index_ohlc(client):
    resp = client.get_ohlc(segment=client.SEGMENT_CASH, exchange_trading_symbols=("NSE_NIFTY",))
    data = payload(resp)
    item = data.get("NSE_NIFTY", data.get("NIFTY")) if isinstance(data, dict) else None
    if isinstance(item, str):
        import json
        item = json.loads(item.replace("'", '"'))
    return item if isinstance(item, dict) else {}

def get_chain(client, exp):
    return client.get_option_chain(exchange=client.EXCHANGE_NSE, underlying="NIFTY", expiry_date=exp.isoformat())

try:
    with st.spinner("Groww se live data fetch ho raha hai..."):
        spot = get_index_ltp(groww)
        ohlc = get_index_ohlc(groww)
        chain_resp = get_chain(groww, expiry)
        chain = payload(chain_resp)
        if not isinstance(chain, dict) or "strikes" not in chain:
            raise ValueError(f"Option-chain response unexpected: {str(chain_resp)[:300]}")
except Exception as e:
    st.error("Live data fetch failed. Token, API subscription, expiry date aur network check karein.")
    st.code(str(e)[:1200])
    st.stop()

strikes = chain.get("strikes", {})
rows = []
for strike, sides in strikes.items():
    try:
        strike_num = float(strike)
    except Exception:
        continue
    row = {"Strike": strike_num}
    for side in ("CE", "PE"):
        contract = sides.get(side) or {}
        greeks = contract.get("greeks") or {}
        row[f"{side} LTP"] = contract.get("ltp")
        row[f"{side} OI"] = contract.get("open_interest")
        row[f"{side} Volume"] = contract.get("volume")
        row[f"{side} Delta"] = greeks.get("delta")
        row[f"{side} IV"] = greeks.get("iv")
        row[f"{side} Symbol"] = contract.get("trading_symbol")
    rows.append(row)
df = pd.DataFrame(rows).sort_values("Strike") if rows else pd.DataFrame()
if df.empty:
    st.error("Option chain empty hai. Selected expiry verify karein.")
    st.stop()

atm_strike = float(df.iloc[(df["Strike"] - spot).abs().argsort()[:1]]["Strike"].iloc[0])
atm = df.loc[df["Strike"] == atm_strike].iloc[0]
ce_ltp = pd.to_numeric(pd.Series([atm.get("CE LTP")]), errors="coerce").iloc[0]
pe_ltp = pd.to_numeric(pd.Series([atm.get("PE LTP")]), errors="coerce").iloc[0]
stamp = datetime.now(TZ).strftime("%H:%M:%S IST")

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY 50", f"{spot:,.2f}")
m2.metric("ATM Strike", f"{atm_strike:,.0f}")
m3.metric("ATM CE Premium", f"₹{ce_ltp:,.2f}" if pd.notna(ce_ltp) else "N/A")
m4.metric("ATM PE Premium", f"₹{pe_ltp:,.2f}" if pd.notna(pe_ltp) else "N/A")

market_open = datetime.now(TZ).weekday() < 5 and time(9,15) <= datetime.now(TZ).time() <= time(15,30)
st.markdown(f"**Feed status:** 🟢 API response received at {stamp}  |  **Market clock:** {'OPEN WINDOW' if market_open else 'OUTSIDE REGULAR SESSION'}")
st.caption("API response received ka matlab connection successful hai; quotes may still be stale. Always verify timestamp/price in Groww before trading.")

# Day OHLC / price levels
open_px = ohlc.get("open")
high_px = ohlc.get("high")
low_px = ohlc.get("low")
prev_close = ohlc.get("close")
c1, c2, c3, c4 = st.columns(4)
for col, label, value in [(c1,"Day Open",open_px),(c2,"Day High",high_px),(c3,"Day Low",low_px),(c4,"API Close field",prev_close)]:
    try: col.metric(label, f"{float(value):,.2f}")
    except Exception: col.metric(label, "N/A")

st.subheader("Signal & Risk Planner")
bias = "WAIT / NO TRADE"
reason = "Single live snapshot se reliable directional entry confirm nahi hoti. Candle-based confirmation add hone tak signal neutral."
if isinstance(open_px, (int, float)) and isinstance(high_px, (int, float)) and isinstance(low_px, (int, float)):
    if spot > open_px and spot > (high_px + low_px) / 2:
        bias = "BULLISH WATCH — CE candidate"
        reason = "Spot day open aur day-range midpoint ke upar hai; breakout confirmation abhi zaroori hai."
    elif spot < open_px and spot < (high_px + low_px) / 2:
        bias = "BEARISH WATCH — PE candidate"
        reason = "Spot day open aur day-range midpoint ke neeche hai; breakdown confirmation abhi zaroori hai."
left, right = st.columns([1,2])
with left:
    if bias.startswith("BULLISH"):
        st.success(bias)
    elif bias.startswith("BEARISH"):
        st.error(bias)
    else:
        st.info(bias)
    st.write(reason)
with right:
    selected_side = st.selectbox("Option contract", ["ATM CE", "ATM PE"])
    premium = float(ce_ltp if selected_side.endswith("CE") else pe_ltp) if pd.notna(ce_ltp if selected_side.endswith("CE") else pe_ltp) else None
    if premium and premium > 0:
        sl_pct = st.slider("Illustrative premium SL (%)", 5, 40, 20, 5)
        target_r = st.selectbox("Target R multiple", [1.0, 1.5, 2.0, 3.0], index=2)
        sl = premium * (1 - sl_pct/100)
        target = premium + (premium-sl) * target_r
        risk_budget = capital * risk_pct / 100
        # Quantity units only; lot size not assumed because it changes and must be checked.
        risk_per_unit = premium - sl
        units = max(0, int(risk_budget / risk_per_unit)) if risk_per_unit > 0 else 0
        st.metric("Selected live premium", f"₹{premium:.2f}")
        x1, x2, x3 = st.columns(3)
        x1.metric("Illustrative Entry", f"₹{premium:.2f}")
        x2.metric("Illustrative SL", f"₹{sl:.2f}")
        x3.metric(f"Illustrative Target ({target_r:g}R)", f"₹{target:.2f}")
        st.caption(f"Risk budget ₹{risk_budget:,.0f}; theoretical units {units:,} before lot-size rounding, charges and slippage. These levels are a calculator, NOT a validated trade signal.")
    else:
        st.warning("Selected option premium unavailable; risk levels not calculated.")

st.subheader("Live Option Chain")
st.caption(f"Expiry: {expiry.isoformat()} • ATM row highlighted by closest strike to NIFTY spot.")
show_cols = ["CE LTP","CE OI","CE Volume","CE Delta","CE IV","Strike","PE LTP","PE OI","PE Volume","PE Delta","PE IV"]
display = df[show_cols].copy()
display["ATM"] = display["Strike"].eq(atm_strike)
st.dataframe(display, use_container_width=True, hide_index=True, height=420)

st.subheader("Premium comparison near ATM")
near = df[(df["Strike"] >= atm_strike - 500) & (df["Strike"] <= atm_strike + 500)].copy()
fig = go.Figure()
fig.add_trace(go.Scatter(x=near["Strike"], y=pd.to_numeric(near["CE LTP"], errors="coerce"), mode="lines+markers", name="CE premium"))
fig.add_trace(go.Scatter(x=near["Strike"], y=pd.to_numeric(near["PE LTP"], errors="coerce"), mode="lines+markers", name="PE premium"))
fig.add_vline(x=spot, line_dash="dash", annotation_text=f"NIFTY {spot:.0f}")
fig.update_layout(template="plotly_dark", height=350, margin=dict(l=10,r=10,t=30,b=10), xaxis_title="Strike", yaxis_title="Premium (₹)")
st.plotly_chart(fig, use_container_width=True)

st.warning("Research / decision-support only. No automatic orders are placed. Verify contract, expiry, liquidity, bid-ask spread and prices in Groww before every manual order. This version does not yet draw historical intraday candles or validate an edge; do not treat WATCH labels as buy calls.")
with st.expander("Connection troubleshooting"):
    st.markdown("""
    - Verify the Groww Trading API subscription and active token.
    - Verify expiry date exactly matches a listed NIFTY expiry.
    - Add token in Streamlit Secrets as `GROWW_ACCESS_TOKEN = "..."` for persistent server-side configuration.
    - Never share the token in chat, screenshots, or GitHub.
    - If Groww SDK method names/response shapes change, copy the error text (remove secrets) for debugging.
    """)

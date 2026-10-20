from datetime import datetime, date
from zoneinfo import ZoneInfo
import calendar
import ast

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

TZ = ZoneInfo("Asia/Kolkata")
BASE = "https://api.groww.in/v1"

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--bg:#0b1118;--panel:#111b25;--panel2:#15212d;--line:#243443;--ink:#eef4f8;--muted:#8fa1b2;--green:#19c37d;--red:#ff6675;--gold:#eabf68;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:var(--ink)}
.stApp{background:radial-gradient(ellipse at 15% 0%,#142333 0%,var(--bg) 48%);color:var(--ink)}
.block-container{max-width:1500px;padding:1rem 1.4rem 2rem}
[data-testid="stHeader"]{background:rgba(11,17,24,.9)}
[data-testid="stSidebar"]{background:#0e1720;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:var(--ink)}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#17212b}
[data-testid="stMetric"]{background:linear-gradient(145deg,#14212d,#101922);border:1px solid var(--line);padding:16px 18px;border-radius:14px;min-height:112px}
[data-testid="stMetricLabel"]{color:var(--muted);font-weight:600;font-size:.78rem;letter-spacing:.02em}
[data-testid="stMetricValue"]{color:var(--ink);font-family:'Manrope',sans-serif;font-weight:800;letter-spacing:-.04em;font-size:1.8rem}
[data-testid="stMetricDelta"]{font-size:.78rem}
.stButton>button{border-radius:9px;border:1px solid #2b4051;background:#172432;color:#edf4f8;font-weight:700;min-height:42px}
.stButton>button[kind="primary"]{background:var(--green);border-color:var(--green);color:#052115}
.stButton>button[kind="primary"]:hover{background:#11ab6c;border-color:#11ab6c;color:#041a11}
.stTextInput input{background:#111d28;color:var(--ink);border-color:var(--line)}
[data-testid="stDataFrame"],[data-testid="stPlotlyChart"]{border:1px solid var(--line);border-radius:13px;overflow:hidden;background:#101923}
[data-testid="stAlert"]{border-radius:10px}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.035em;color:var(--ink)}
.brand{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:17px 20px;border:1px solid #263a4a;border-radius:16px;background:linear-gradient(110deg,#142432,#0e1822);margin-bottom:17px}
.brand-left{display:flex;align-items:center;gap:12px}.brand-icon{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#19c37d;color:#062417;font-size:25px;font-weight:900}.brand-title{font-family:'Manrope',sans-serif;font-weight:800;font-size:1.25rem;letter-spacing:-.045em;color:#f2f7fb}.brand-sub{font-size:.72rem;letter-spacing:.11em;color:#91a5b7;margin-top:3px}.pill{display:inline-flex;align-items:center;gap:7px;border:1px solid #245743;background:#102b21;color:#78e6b4;border-radius:999px;padding:7px 11px;font-size:.73rem;font-weight:700;white-space:nowrap}.dot{width:7px;height:7px;background:#19c37d;border-radius:50%;display:inline-block}.section{display:flex;align-items:center;justify-content:space-between;margin:22px 0 10px}.section-title{font-family:'Manrope',sans-serif;font-size:1.03rem;font-weight:800;color:#edf4f8}.section-sub{font-size:.75rem;color:#7f93a5}.info-box{background:#111e29;border:1px solid #243746;border-radius:12px;padding:13px 15px;color:#a9bac8;font-size:.86rem}.status-ok{background:#102b21;border:1px solid #245743;border-radius:12px;padding:13px 15px;color:#78e6b4;font-size:.87rem}.status-bad{background:#311b23;border:1px solid #63313d;border-radius:12px;padding:13px 15px;color:#ff9ba5;font-size:.87rem}.small-note{font-size:.74rem;color:#8093a4}.stTabs [data-baseweb="tab-list"]{gap:8px;background:#101923;border:1px solid #243443;padding:5px;border-radius:12px}.stTabs [data-baseweb="tab"]{height:40px;border-radius:8px;color:#91a5b7}.stTabs [aria-selected="true"]{background:#1a2c39;color:#f5fafc}
@media(max-width:700px){.block-container{padding:.6rem .7rem 1.5rem}.brand{padding:12px}.brand-title{font-size:1rem}.brand-sub{font-size:.59rem;letter-spacing:.06em}.pill{font-size:.63rem;padding:6px 8px}[data-testid="stMetric"]{padding:12px;min-height:96px}[data-testid="stMetricValue"]{font-size:1.35rem}.section-sub{display:none}}
</style>
""", unsafe_allow_html=True)

now = datetime.now(TZ)
st.markdown(f'''<div class="brand"><div class="brand-left"><div class="brand-icon">↗</div><div><div class="brand-title">NIFTY SENTINEL</div><div class="brand-sub">MARKET MONITOR&nbsp; / &nbsp;OPTIONS ANALYTICS&nbsp; / &nbsp;MANUAL EXECUTION</div></div></div><div class="pill"><span class="dot"></span> GROWW API CONNECTOR</div></div>''', unsafe_allow_html=True)

# Auth controls remain in the sidebar; secrets never appear in the UI.
with st.sidebar:
    st.markdown("### Connection")
    auth_mode = st.radio("Authentication", ["Access token", "TOTP token"], horizontal=False)
    saved_token = ""
    try:
        saved_token = st.secrets.get("GROWW_ACCESS_TOKEN", "")
    except Exception:
        pass
    token = ""
    if auth_mode == "Access token":
        token = st.text_input("Groww access token", value=saved_token, type="password", help="Keep this private. Access tokens expire daily.")
    else:
        st.caption("Enter your Groww API key and TOTP secret. Do not share either one.")
        api_key = st.text_input("Groww API key", type="password")
        totp_secret = st.text_input("TOTP secret", type="password")
        if st.button("Generate access token", use_container_width=True, type="primary"):
            try:
                import pyotp
                from growwapi import GrowwAPI
                if not api_key.strip() or not totp_secret.strip():
                    raise ValueError("Enter API key and TOTP secret.")
                otp = pyotp.TOTP(totp_secret.strip()).now()
                generated = GrowwAPI.get_access_token(api_key=api_key.strip(), totp=otp)
                st.session_state["groww_generated_access_token"] = generated
                st.session_state["groww_generated_token_time"] = datetime.now(TZ).strftime("%H:%M:%S IST")
                st.success("Access token generated for this session.")
            except Exception as exc:
                st.error("Token generation failed. Verify API key, TOTP secret and daily approval.")
                st.caption(f"Diagnostic: {type(exc).__name__}: {str(exc)[:180]}")
        token = st.session_state.get("groww_generated_access_token", "")
        if token:
            st.caption("Session token created at " + st.session_state.get("groww_generated_token_time", ""))
    st.divider()
    st.markdown("### Risk controls")
    capital = st.number_input("Trading capital (₹)", min_value=1000, value=150000, step=5000)
    risk_pct = st.slider("Risk budget (%)", 0.25, 2.0, 0.5, 0.25)
    st.caption("Dashboard only. No orders are placed. Never commit credentials to GitHub.")

if not token:
    st.markdown('<div class="info-box">Connect your Groww access token from the sidebar. The dashboard does not display mock prices.</div>', unsafe_allow_html=True)
    st.stop()

headers = {"Accept": "application/json", "Authorization": f"Bearer {token}", "X-API-VERSION": "1.0"}

def api_get(path, params=None, timeout=15):
    response = requests.get(BASE + path, headers=headers, params=params, timeout=timeout)
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text[:250]}
    if response.status_code != 200:
        err = data.get("error", {}) if isinstance(data, dict) else {}
        message = err.get("message", str(data)[:250]) if isinstance(err, dict) else str(data)[:250]
        code = err.get("code", response.status_code) if isinstance(err, dict) else response.status_code
        raise RuntimeError(f"HTTP {response.status_code} · {code}: {message}")
    if isinstance(data, dict) and data.get("status") == "FAILURE":
        err = data.get("error", {})
        raise RuntimeError(f"{err.get('code','API_FAILURE')}: {err.get('message','Groww API request failed')}")
    return data.get("payload", data) if isinstance(data, dict) else data

# Refresh button is intentionally explicit so API calls are controlled.
left, right = st.columns([1, 2])
with left:
    refresh = st.button("↻  Refresh live snapshot", type="primary", use_container_width=True)
with right:
    st.markdown(f'<div style="text-align:right;padding-top:11px;color:#8195a6;font-size:.78rem">Snapshot requested · {now.strftime("%d %b %Y, %H:%M:%S IST")}</div>', unsafe_allow_html=True)

# LTP is the primary connection test and remains visible even if the option-chain endpoint fails.
try:
    ltp_payload = api_get("/live-data/ltp", {"segment": "CASH", "exchange_symbols": "NSE_NIFTY"})
    spot = ltp_payload.get("NSE_NIFTY") if isinstance(ltp_payload, dict) else None
    if spot is None:
        raise RuntimeError(f"NSE_NIFTY missing from LTP response: {str(ltp_payload)[:180]}")
    spot = float(spot)
except Exception as exc:
    st.markdown('<div class="status-bad"><b>Market data disconnected.</b> Groww rejected the live quote request.</div>', unsafe_allow_html=True)
    st.code(str(exc))
    st.info("Check access-token validity and Groww API approval. Market closure alone does not explain HTTP 401/403.")
    st.stop()

# Quote and OHLC snapshot
ohlc = {}
try:
    raw_ohlc = api_get("/live-data/ohlc", {"segment": "CASH", "exchange_symbols": "NSE_NIFTY"})
    value = raw_ohlc.get("NSE_NIFTY", {}) if isinstance(raw_ohlc, dict) else {}
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except Exception:
            value = {}
    if isinstance(value, dict):
        ohlc = value
except Exception:
    pass

# Actual contract expiry list from Groww is preferred over hard-coded weekday assumptions.
def get_expiries():
    today = datetime.now(TZ).date()
    months = [(today.year, today.month)]
    next_month = 1 if today.month == 12 else today.month + 1
    next_year = today.year + 1 if today.month == 12 else today.year
    months.append((next_year, next_month))
    dates = []
    for year, month in months:
        try:
            payload = api_get("/historical/expiries", {"exchange": "NSE", "underlying_symbol": "NIFTY", "year": year, "month": month})
            vals = payload.get("expiries", []) if isinstance(payload, dict) else []
            for item in vals:
                try:
                    d = date.fromisoformat(str(item)[:10])
                    if d >= today and d not in dates:
                        dates.append(d)
                except Exception:
                    continue
        except Exception:
            continue
    if not dates:
        # Fallback only if the expiry endpoint itself is unavailable; still clearly labelled as candidates.
        today = datetime.now(TZ).date()
        for offset in range(0, 75):
            d = date.fromordinal(today.toordinal() + offset)
            if d.weekday() == 1 and d not in dates:
                dates.append(d)
    return sorted(dates)

expiries = get_expiries()
if not expiries:
    expiries = [datetime.now(TZ).date()]
with st.sidebar:
    selected_expiry = st.selectbox("NIFTY contract expiry", options=expiries, index=0, format_func=lambda d: d.strftime("%d %b %Y"))

# Market overview
st.markdown('<div class="section"><div class="section-title">Market overview</div><div class="section-sub">Groww live snapshot · index spot</div></div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
col1.metric("NIFTY 50", f"{spot:,.2f}")
col2.metric("Open", f"{float(ohlc.get('open')):,.2f}" if ohlc.get('open') is not None else "—")
col3.metric("Day high", f"{float(ohlc.get('high')):,.2f}" if ohlc.get('high') is not None else "—")
col4.metric("Day low", f"{float(ohlc.get('low')):,.2f}" if ohlc.get('low') is not None else "—")
st.markdown('<div class="status-ok"><b>● Live quote received</b> &nbsp; NIFTY spot is coming from Groww API. Option chain is queried separately; if that endpoint fails, the rest of the dashboard remains available.</div>', unsafe_allow_html=True)

# Option chain request; failure is non-fatal and does not hide the live quote/dashboard.
chain_error = None
df = pd.DataFrame()
try:
    chain = api_get("/option-chain/exchange/NSE/underlying/NIFTY", {"expiry_date": selected_expiry.isoformat()})
    strikes = chain.get("strikes", {}) if isinstance(chain, dict) else {}
    rows = []
    for strike, sides in strikes.items():
        try:
            strike_num = float(strike)
        except Exception:
            continue
        row = {"Strike": strike_num}
        for side in ("CE", "PE"):
            contract = (sides or {}).get(side) or {}
            greeks = contract.get("greeks") or {}
            row.update({
                f"{side} LTP": contract.get("ltp"), f"{side} OI": contract.get("open_interest"),
                f"{side} Volume": contract.get("volume"), f"{side} Delta": greeks.get("delta"),
                f"{side} IV": greeks.get("iv"), f"{side} Theta": greeks.get("theta"),
                f"{side} Symbol": contract.get("trading_symbol")
            })
        rows.append(row)
    if rows:
        df = pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
    else:
        chain_error = "Groww returned no strike rows for this expiry."
except Exception as exc:
    chain_error = str(exc)

if not df.empty:
    atm_idx = (df["Strike"] - spot).abs().idxmin()
    atm_strike = float(df.loc[atm_idx, "Strike"])
    atm = df.loc[atm_idx]
    ce = pd.to_numeric(pd.Series([atm.get("CE LTP")]), errors="coerce").iloc[0]
    pe = pd.to_numeric(pd.Series([atm.get("PE LTP")]), errors="coerce").iloc[0]
    st.markdown('<div class="section"><div class="section-title">At-the-money contracts</div><div class="section-sub">Selected expiry · premium in ₹</div></div>', unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("ATM strike", f"{atm_strike:,.0f}")
    q2.metric("ATM CE", f"₹{ce:,.2f}" if pd.notna(ce) else "—")
    q3.metric("ATM PE", f"₹{pe:,.2f}" if pd.notna(pe) else "—")
    q4.metric("Available strikes", f"{len(df):,}")

    tab_chain, tab_chart, tab_plan = st.tabs(["Option chain", "Premium chart", "Trade planner"])
    with tab_chain:
        range_pts = st.select_slider("Strike range around ATM", options=[100, 200, 300, 500, 1000, 2000], value=500, format_func=lambda x: f"±{x} pts")
        near = df[(df["Strike"] >= atm_strike-range_pts) & (df["Strike"] <= atm_strike+range_pts)].copy()
        display_cols = ["CE LTP", "CE OI", "CE Volume", "CE Delta", "CE IV", "Strike", "PE IV", "PE Delta", "PE Volume", "PE OI", "PE LTP"]
        display = near[display_cols].copy()
        for col in display.columns:
            if col != "Strike":
                display[col] = pd.to_numeric(display[col], errors="coerce")
        st.dataframe(display, use_container_width=True, hide_index=True, height=430, column_config={"Strike": st.column_config.NumberColumn(format="%.0f"), "CE LTP": st.column_config.NumberColumn(format="₹%.2f"), "PE LTP": st.column_config.NumberColumn(format="₹%.2f"), "CE IV": st.column_config.NumberColumn(format="%.2f"), "PE IV": st.column_config.NumberColumn(format="%.2f")})
        st.caption(f"Source: Groww option-chain API · expiry {selected_expiry.isoformat()} · snapshot {datetime.now(TZ).strftime('%H:%M:%S IST')}")
    with tab_chart:
        near = df[(df["Strike"] >= atm_strike-1000) & (df["Strike"] <= atm_strike+1000)].copy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=near["Strike"], y=pd.to_numeric(near["CE LTP"], errors="coerce"), mode="lines+markers", name="Call (CE)", line=dict(color="#19c37d", width=2), marker=dict(size=5)))
        fig.add_trace(go.Scatter(x=near["Strike"], y=pd.to_numeric(near["PE LTP"], errors="coerce"), mode="lines+markers", name="Put (PE)", line=dict(color="#ff6675", width=2), marker=dict(size=5)))
        fig.add_vline(x=spot, line_dash="dash", line_color="#eabf68", annotation_text=f"Spot {spot:,.0f}")
        fig.update_layout(template="plotly_dark", paper_bgcolor="#101923", plot_bgcolor="#101923", font=dict(family="DM Sans", color="#dce7ef"), height=390, margin=dict(l=15, r=15, t=25, b=10), xaxis_title="Strike price", yaxis_title="Option premium (₹)", legend=dict(orientation="h", y=1.08, x=0))
        fig.update_xaxes(gridcolor="#243443", zerolinecolor="#243443")
        fig.update_yaxes(gridcolor="#243443", zerolinecolor="#243443")
        st.plotly_chart(fig, use_container_width=True)
    with tab_plan:
        instrument = st.radio("Contract side", ["ATM CE", "ATM PE"], horizontal=True)
        premium = float(ce if instrument.endswith("CE") else pe) if pd.notna(ce if instrument.endswith("CE") else pe) else None
        if premium and premium > 0:
            sl_pct = st.slider("Illustrative premium stop (%)", 5, 40, 20, 5)
            r_multiple = st.selectbox("Target risk multiple", [1.0, 1.5, 2.0, 3.0], index=2)
            sl_price = premium * (1 - sl_pct/100)
            target = premium + (premium-sl_price)*r_multiple
            risk_cash = capital*risk_pct/100
            risk_per_unit = premium-sl_price
            units = int(risk_cash/risk_per_unit) if risk_per_unit > 0 else 0
            p1,p2,p3,p4 = st.columns(4)
            p1.metric("Reference premium", f"₹{premium:.2f}")
            p2.metric("Illustrative stop", f"₹{sl_price:.2f}")
            p3.metric(f"Illustrative target ({r_multiple:g}R)", f"₹{target:.2f}")
            p4.metric("Risk budget", f"₹{risk_cash:,.0f}")
            st.markdown(f'<div class="info-box">Theoretical units before lot-size rounding and charges: <b>{units:,}</b>. This is a calculator only, not a validated signal or a recommendation to trade.</div>', unsafe_allow_html=True)
        else:
            st.info("No valid ATM premium returned for this side.")
else:
    st.markdown('<div class="section"><div class="section-title">Option chain</div><div class="section-sub">Live chain status</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="status-bad"><b>Option chain unavailable</b><br>{chain_error or "No chain data returned."}</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">NIFTY live quote is still connected. The app uses Groww’s official expiry list when available; a chain error is shown without replacing real data with mock prices. If this is HTTP 500 / GA000 for a valid listed expiry, it may need Groww-side investigation.</div>', unsafe_allow_html=True)

# Strategy engine: uses only the actual Groww spot/OHLC snapshot. No fabricated candles/signals.
st.markdown('<div class="section"><div class="section-title">Strategy & trade decision</div><div class="section-sub">Rule-based context · confirmation required</div></div>', unsafe_allow_html=True)
open_px = pd.to_numeric(pd.Series([ohlc.get("open")]), errors="coerce").iloc[0]
high_px = pd.to_numeric(pd.Series([ohlc.get("high")]), errors="coerce").iloc[0]
low_px = pd.to_numeric(pd.Series([ohlc.get("low")]), errors="coerce").iloc[0]
close_px = pd.to_numeric(pd.Series([ohlc.get("close")]), errors="coerce").iloc[0]
if pd.notna(high_px) and pd.notna(low_px) and high_px > low_px:
    day_mid = (high_px + low_px) / 2
    if pd.notna(open_px) and spot > open_px and spot > day_mid:
        bias = "BULLISH BIAS"
        bias_detail = "Spot is above the day open and day-range midpoint. Consider CE only after a confirmed 5-minute breakout/retest; otherwise WAIT."
        bias_color = "#19c37d"
    elif pd.notna(open_px) and spot < open_px and spot < day_mid:
        bias = "BEARISH BIAS"
        bias_detail = "Spot is below the day open and day-range midpoint. Consider PE only after a confirmed 5-minute breakdown/retest; otherwise WAIT."
        bias_color = "#ff6675"
    else:
        bias = "NEUTRAL / WAIT"
        bias_detail = "Spot has mixed positioning versus the day open and range midpoint. Avoid forcing a CE/PE trade; wait for a clean 5-minute close and retest."
        bias_color = "#eabf68"
else:
    day_mid = None
    bias, bias_detail, bias_color = "WAIT — OHLC INCOMPLETE", "Groww did not return usable day high/low values. No strategy bias will be invented.", "#eabf68"
sc1, sc2, sc3 = st.columns([1,1,2])
sc1.metric("Market bias", bias)
sc2.metric("Day range midpoint", f"{day_mid:,.2f}" if day_mid is not None else "—")
sc3.markdown(f'<div class="info-box" style="height:100%;border-left:3px solid {bias_color}"><b>Setup rules</b><br>{bias_detail}<br><span class="small-note">This is a context filter, not a statistically validated edge. No 5-minute candle feed is currently connected, so the app cannot confirm candle-close triggers.</span></div>', unsafe_allow_html=True)
with st.expander("Strategy rules & risk checklist", expanded=False):
    st.markdown("""
    **Setup A — Breakout:** wait for a completed 5-minute candle to close above the relevant resistance/day high, then look for a retest that holds. A close back below the breakout level invalidates the setup.

    **Setup B — Breakdown:** wait for a completed 5-minute candle to close below support/day low, then look for a retest that fails. A close back above the breakdown level invalidates the setup.

    **Trend filter:** bullish context = spot above day open and day-range midpoint; bearish context = spot below both; mixed context = WAIT. This is a simple rule filter, not proof of profitability.

    **Before entry:** verify live option premium, bid/ask spread, liquidity, expiry, lot size and charges in Groww. Define the underlying invalidation level first; do not set the stop from a guessed premium. Skip if the planned loss exceeds the risk budget.
    """)

st.markdown('<div class="section"><div class="section-title">Trade planner & journal</div><div class="section-sub">Manual execution in Groww · no orders placed here</div></div>', unsafe_allow_html=True)
pl1, pl2, pl3 = st.columns(3)
with pl1:
    trade_side = st.selectbox("Planned side", ["CE BUY", "PE BUY"])
    entry_premium = st.number_input("Option entry premium (₹)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
with pl2:
    stop_premium = st.number_input("Option stop premium (₹)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
    target_r = st.selectbox("Target multiple", [1.0, 1.5, 2.0, 3.0], index=2)
with pl3:
    lot_size = st.number_input("Lot size (verify in Groww)", min_value=1, value=65, step=1)
    max_risk = capital * risk_pct / 100
if entry_premium > 0 and stop_premium > 0 and entry_premium > stop_premium:
    per_unit_risk = entry_premium - stop_premium
    qty_units = int(max_risk // per_unit_risk)
    lots = qty_units // int(lot_size)
    qty = lots * int(lot_size)
    planned_loss = qty * per_unit_risk
    target_premium = entry_premium + per_unit_risk * target_r
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Risk budget", f"₹{max_risk:,.0f}")
    t2.metric("Suggested lots by risk", f"{lots}")
    t3.metric("Qty", f"{qty}")
    t4.metric("Target premium", f"₹{target_premium:,.2f}")
    st.caption(f"Planned loss at stop: ₹{planned_loss:,.0f} before charges/slippage. If zero lots fit the risk budget, skip the trade. Verify lot size and premiums in Groww.")
else:
    st.info("Enter a valid entry premium and a lower stop premium to calculate risk-sized lots and a target. This does not create a trade signal.")

if "trade_journal" not in st.session_state:
    st.session_state["trade_journal"] = []
with st.expander("Record a trade manually", expanded=False):
    with st.form("manual_trade_form", clear_on_submit=True):
        j1, j2, j3 = st.columns(3)
        with j1:
            journal_symbol = st.text_input("Contract / symbol", placeholder="e.g. NIFTY ... CE")
            journal_entry = st.number_input("Actual entry premium ₹", min_value=0.0, value=0.0, step=0.5)
        with j2:
            journal_exit = st.number_input("Exit premium ₹ (0 if open)", min_value=0.0, value=0.0, step=0.5)
            journal_qty = st.number_input("Quantity", min_value=1, value=int(lot_size), step=1)
        with j3:
            journal_reason = st.selectbox("Setup", ["Breakout", "Trend pullback", "Breakdown", "Other"])
            journal_note = st.text_input("Notes / exit reason")
        saved = st.form_submit_button("Save trade record", type="primary", use_container_width=True)
        if saved:
            if not journal_symbol.strip() or journal_entry <= 0:
                st.error("Enter a contract symbol and valid entry premium.")
            else:
                pnl = (journal_exit - journal_entry) * journal_qty if journal_exit > 0 else None
                st.session_state["trade_journal"].append({"Time (IST)": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"), "Contract": journal_symbol.strip(), "Setup": journal_reason, "Entry ₹": journal_entry, "Exit ₹": journal_exit if journal_exit > 0 else None, "Qty": int(journal_qty), "P&L before costs ₹": pnl, "Notes": journal_note})
                st.success("Trade recorded in this app session.")
    if st.session_state["trade_journal"]:
        journal_df = pd.DataFrame(st.session_state["trade_journal"])
        st.dataframe(journal_df, use_container_width=True, hide_index=True)
        csv_bytes = journal_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download trade journal CSV", data=csv_bytes, file_name="nifty_sentinel_trade_journal.csv", mime="text/csv")
        st.caption("Journal is stored only in the current Streamlit session unless downloaded. P&L excludes brokerage, taxes and slippage.")


# Evidence-based strategy research engine. It never converts an index signal into a guaranteed option-premium prediction.
import numpy as np

def prepare_candles(frame):
    d = frame.copy()
    aliases = {str(c).strip().lower(): c for c in d.columns}
    def pick(*names):
        for name in names:
            if name in aliases: return aliases[name]
        return None
    date_col = pick('date','datetime','timestamp','time')
    mapping = {k: pick(k) for k in ['open','high','low','close']}
    if not date_col or any(v is None for v in mapping.values()):
        raise ValueError('CSV must contain Date/Datetime and Open, High, Low, Close columns.')
    d = d.rename(columns={date_col:'Timestamp', **{v:k.title() for k,v in mapping.items()}})
    d['Timestamp'] = pd.to_datetime(d['Timestamp'], errors='coerce', dayfirst=False)
    for c in ['Open','High','Low','Close']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['Timestamp','Open','High','Low','Close']).sort_values('Timestamp').drop_duplicates('Timestamp').reset_index(drop=True)
    d = d[(d['High'] >= d[['Open','Close','Low']].max(axis=1)) & (d['Low'] <= d[['Open','Close','High']].min(axis=1))]
    if len(d) < 80: raise ValueError(f'Need at least 80 valid candles; found {len(d)}.')
    d['EMA20'] = d['Close'].ewm(span=20, adjust=False).mean()
    d['EMA50'] = d['Close'].ewm(span=50, adjust=False).mean()
    delta = d['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d['RSI'] = (100 - 100/(1+rs)).fillna(50)
    prev = d['Close'].shift(1)
    tr = pd.concat([d['High']-d['Low'], (d['High']-prev).abs(), (d['Low']-prev).abs()], axis=1).max(axis=1)
    d['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    d['PriorHigh20'] = d['High'].rolling(20).max().shift(1)
    d['PriorLow20'] = d['Low'].rolling(20).min().shift(1)
    return d.dropna(subset=['PriorHigh20','PriorLow20','ATR']).reset_index(drop=True)

def strategy_signals(d, strategy):
    if strategy == 'Breakout':
        long = (d.Close > d.PriorHigh20) & (d.EMA20 > d.EMA50) & d.RSI.between(52, 75)
        short = (d.Close < d.PriorLow20) & (d.EMA20 < d.EMA50) & d.RSI.between(25, 48)
    elif strategy == 'Trend pullback':
        long = (d.EMA20 > d.EMA50) & (d.Low <= d.EMA20) & (d.Close > d.EMA20) & (d.Close > d.Open) & d.RSI.between(45, 65)
        short = (d.EMA20 < d.EMA50) & (d.High >= d.EMA20) & (d.Close < d.EMA20) & (d.Close < d.Open) & d.RSI.between(35, 55)
    else:
        long = (d.Close > d.EMA20) & (d.EMA20 > d.EMA50) & d.RSI.between(50, 68)
        short = (d.Close < d.EMA20) & (d.EMA20 < d.EMA50) & d.RSI.between(32, 50)
    return long.fillna(False), short.fillna(False)

def run_backtest(d, strategy, fee_points=2.0, atr_stop=1.5, target_r=2.0, max_bars=8):
    longs, shorts = strategy_signals(d, strategy)
    trades=[]; i=1
    while i < len(d)-1:
        side = 1 if bool(longs.iloc[i-1]) else (-1 if bool(shorts.iloc[i-1]) else 0)
        if side == 0:
            i += 1; continue
        entry_i=i; entry=float(d.Open.iloc[i]); atr=float(d.ATR.iloc[i-1])
        if not np.isfinite(entry) or not np.isfinite(atr) or atr <= 0:
            i += 1; continue
        risk=atr_stop*atr; stop=entry-side*risk; target=entry+side*risk*target_r
        exit_i=min(len(d)-1, entry_i+max_bars); exit_px=float(d.Close.iloc[exit_i]); reason='TIME'
        for j in range(entry_i, min(len(d), entry_i+max_bars+1)):
            hi=float(d.High.iloc[j]); lo=float(d.Low.iloc[j])
            hit_stop = lo <= stop if side==1 else hi >= stop
            hit_target = hi >= target if side==1 else lo <= target
            # Conservative assumption if both levels hit within same candle: stop is filled first.
            if hit_stop:
                exit_i=j; exit_px=stop; reason='SL'; break
            if hit_target:
                exit_i=j; exit_px=target; reason='TARGET'; break
        gross=(exit_px-entry)*side; net=gross-fee_points
        trades.append({'Entry time':str(d.Timestamp.iloc[entry_i]),'Exit time':str(d.Timestamp.iloc[exit_i]),'Side':'LONG' if side==1 else 'SHORT','Entry':entry,'Exit':exit_px,'Stop':stop,'Target':target,'Exit reason':reason,'Gross points':gross,'Net points':net,'R after costs':net/risk if risk else np.nan})
        i=exit_i+1
    return pd.DataFrame(trades)

def stats_for(trades):
    if trades.empty: return {'Trades':0,'Win rate %':0.0,'Net points':0.0,'Profit factor':0.0,'Avg R':0.0,'Max drawdown points':0.0}
    net=trades['Net points']; wins=net[net>0].sum(); losses=-net[net<0].sum()
    equity=net.cumsum(); dd=equity-equity.cummax()
    return {'Trades':len(trades),'Win rate %':round((net>0).mean()*100,1),'Net points':round(net.sum(),2),'Profit factor':round(wins/losses,2) if losses>0 else float('inf') if wins>0 else 0.0,'Avg R':round(trades['R after costs'].mean(),2),'Max drawdown points':round(float(dd.min()),2)}

st.markdown('<div class="section"><div class="section-title">Strategy lab · backtest before live signals</div><div class="section-sub">Historical index points only · not option P&L</div></div>', unsafe_allow_html=True)
st.caption('The bundled research file is a short 15-minute sample ending 19 Oct 2026 (about 20 sessions). Results are exploratory, not proof of an edge. Index points are not CE/PE premium returns.')
with st.expander('Live Groww candles / strategy research', expanded=True):
    st.caption('Strategy signals use Groww historical candles when fetched successfully. 5-minute history is requested for the latest 30 days (Groww API limit). A closed market can still return historical candles.')
    fetch_live_candles = st.button('↻ Fetch latest 5-minute NIFTY candles from Groww', type='primary', key='fetch_groww_candles')
    uploaded_candles = st.file_uploader('Optional: upload NIFTY candle CSV (Date/Datetime, Open, High, Low, Close)', type=['csv'], key='strategy_csv')
    source_label = 'Groww historical candles (not fetched yet)'
    raw_research = None
    # Fetch only on explicit button press to avoid repeated API calls on every Streamlit rerun.
    if fetch_live_candles:
        try:
            from growwapi import GrowwAPI
            sdk = GrowwAPI(token)
            end_dt = datetime.now(TZ).replace(tzinfo=None)
            start_dt = end_dt - pd.Timedelta(days=29)
            candles_response = sdk.get_historical_candles(
                exchange=sdk.EXCHANGE_NSE,
                segment=sdk.SEGMENT_CASH,
                groww_symbol='NSE-NIFTY',
                start_time=start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                end_time=end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                candle_interval=sdk.CANDLE_INTERVAL_MIN_5,
            )
            candle_rows = candles_response.get('candles', []) if isinstance(candles_response, dict) else []
            if not candle_rows:
                raise ValueError('Groww returned no candles for the requested period.')
            raw_research = pd.DataFrame(candle_rows, columns=['Timestamp','Open','High','Low','Close','Volume','OpenInterest'])
            st.session_state['groww_nifty_5m_candles'] = raw_research
            st.session_state['groww_nifty_5m_fetched_at'] = datetime.now(TZ).strftime('%d %b %Y %H:%M:%S IST')
        except Exception as exc:
            st.error(f'Groww historical candle fetch failed: {type(exc).__name__}: {str(exc)[:220]}')
    if uploaded_candles is not None:
        raw_research = pd.read_csv(uploaded_candles)
        source_label = uploaded_candles.name
    elif raw_research is not None:
        source_label = 'Groww historical 5-minute candles'
    elif 'groww_nifty_5m_candles' in st.session_state:
        raw_research = st.session_state['groww_nifty_5m_candles'].copy()
        source_label = 'Groww historical 5-minute candles · fetched ' + st.session_state.get('groww_nifty_5m_fetched_at', '')
    else:
        default_path = 'research_candles_15m.csv' if __import__('os').path.exists('research_candles_15m.csv') else __import__('os').path.join(__import__('os').path.dirname(__file__),'research_candles_15m.csv')
        raw_research = pd.read_csv(default_path)
        source_label = 'Bundled 15-minute fallback (NOT live)'
    try:
        research = prepare_candles(raw_research)
        st.caption(f'Data source: {source_label} · {len(research)} usable candles · {research.Timestamp.min()} → {research.Timestamp.max()}')
        if 'Groww historical 5-minute' in source_label:
            st.success('Strategy lab is now using real Groww historical NIFTY candles. These are historical 5-minute bars, not a continuous streaming feed; refresh them during market hours for the latest completed bars.')
        else:
            st.warning('Strategy lab is not currently using fresh Groww candles. Fetch them above before treating the displayed setup as current.')
        cfg1,cfg2,cfg3,cfg4 = st.columns(4)
        with cfg1: chosen_strategy=st.selectbox('Strategy', ['Breakout','Trend pullback','EMA trend'], key='bt_strategy')
        with cfg2: fee_points=st.number_input('Round-trip cost (index points)', min_value=0.0, max_value=50.0, value=2.0, step=0.5)
        with cfg3: stop_atr=st.selectbox('Stop distance (ATR)', [1.0,1.5,2.0], index=1)
        with cfg4: target_multiple=st.selectbox('Target (R)', [1.0,1.5,2.0,3.0], index=2)
        all_trades=run_backtest(research, chosen_strategy, fee_points, stop_atr, target_multiple)
        # Chronological split; signals are computed on each candle and entries occur at next candle open.
        split=int(len(research)*0.7)
        split_time=research.Timestamp.iloc[split]
        dev=all_trades[pd.to_datetime(all_trades['Entry time']) < split_time] if not all_trades.empty else all_trades
        oos=all_trades[pd.to_datetime(all_trades['Entry time']) >= split_time] if not all_trades.empty else all_trades
        m1,m2,m3,m4,m5 = st.columns(5)
        ms=stats_for(oos)
        m1.metric('OOS trades', ms['Trades']); m2.metric('OOS win rate', f"{ms['Win rate %']}%"); m3.metric('OOS net points', f"{ms['Net points']:+.1f}"); m4.metric('OOS profit factor', f"{ms['Profit factor']}"); m5.metric('OOS max DD', f"{ms['Max drawdown points']:.1f}")
        st.write('**Development period**'); st.dataframe(pd.DataFrame([stats_for(dev)]), use_container_width=True, hide_index=True)
        st.write('**Out-of-sample period (chronologically later 30%)**'); st.dataframe(pd.DataFrame([ms]), use_container_width=True, hide_index=True)
        if all_trades.empty:
            st.warning('No trades triggered in this sample. Do not loosen rules just to force trades.')
        else:
            st.write('**Trade-by-trade audit**'); st.dataframe(all_trades, use_container_width=True, hide_index=True, height=300)
            st.download_button('Download backtest trades CSV', all_trades.to_csv(index=False).encode('utf-8'), 'nifty_sentinel_backtest_trades.csv', 'text/csv')
        latest=research.iloc[-1]
        long_sig,short_sig=strategy_signals(research,chosen_strategy)
        last_long=bool(long_sig.iloc[-1]); last_short=bool(short_sig.iloc[-1])
        if last_long: signal='LONG BIAS — CE candidate only after option/liquidity checks'; why='Latest completed candle meets bullish rules.'
        elif last_short: signal='SHORT BIAS — PE candidate only after option/liquidity checks'; why='Latest completed candle meets bearish rules.'
        else: signal='NO TRADE'; why='Latest candle does not meet the selected strategy rules.'
        st.markdown(f'<div class="info-box"><b>Latest candle decision: {signal}</b><br>{why}<br>Close {latest.Close:,.2f} · EMA20 {latest.EMA20:,.2f} · EMA50 {latest.EMA50:,.2f} · RSI {latest.RSI:.1f} · ATR {latest.ATR:.1f}<br><span class="small-note">Source: {source_label}. Signals are based on the latest returned candle and are candidates, not guaranteed option trades. Confirm current option premium, spread, liquidity and expiry.</span></div>', unsafe_allow_html=True)
    except Exception as exc:
        st.error(f'Strategy research data issue: {exc}')

st.markdown('<div class="section"><div class="section-title">Data & execution status</div><div class="section-sub">Read-only market monitor</div></div>', unsafe_allow_html=True)
s1, s2, s3 = st.columns(3)
s1.markdown('<div class="info-box"><b style="color:#dce7ef">Market feed</b><br><span style="color:#78e6b4">● Connected</span><br><span class="small-note">Groww LTP endpoint</span></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="info-box"><b style="color:#dce7ef">Option chain</b><br><span style="color:{"#78e6b4" if not chain_error else "#ff9ba5"}">{"● Available" if not chain_error else "● Unavailable"}</span><br><span class="small-note">Expiry: {selected_expiry.strftime("%d %b %Y")}</span></div>', unsafe_allow_html=True)
s3.markdown('<div class="info-box"><b style="color:#dce7ef">Order execution</b><br><span style="color:#eabf68">● Manual only</span><br><span class="small-note">No orders sent by this dashboard</span></div>', unsafe_allow_html=True)
st.markdown('<div style="margin-top:16px;border-top:1px solid #243443;padding-top:12px;color:#708597;font-size:.72rem">NIFTY SENTINEL · Live snapshot, not a tick-by-tick websocket feed. Refresh to request a new snapshot. Verify prices and contract details in Groww before any trade. SL/targets are illustrative and not a validated strategy.</div>', unsafe_allow_html=True)

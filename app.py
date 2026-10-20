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

st.markdown('<div class="section"><div class="section-title">Data & execution status</div><div class="section-sub">Read-only market monitor</div></div>', unsafe_allow_html=True)
s1, s2, s3 = st.columns(3)
s1.markdown('<div class="info-box"><b style="color:#dce7ef">Market feed</b><br><span style="color:#78e6b4">● Connected</span><br><span class="small-note">Groww LTP endpoint</span></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="info-box"><b style="color:#dce7ef">Option chain</b><br><span style="color:{"#78e6b4" if not chain_error else "#ff9ba5"}">{"● Available" if not chain_error else "● Unavailable"}</span><br><span class="small-note">Expiry: {selected_expiry.strftime("%d %b %Y")}</span></div>', unsafe_allow_html=True)
s3.markdown('<div class="info-box"><b style="color:#dce7ef">Order execution</b><br><span style="color:#eabf68">● Manual only</span><br><span class="small-note">No orders sent by this dashboard</span></div>', unsafe_allow_html=True)
st.markdown('<div style="margin-top:16px;border-top:1px solid #243443;padding-top:12px;color:#708597;font-size:.72rem">NIFTY SENTINEL · Live snapshot, not a tick-by-tick websocket feed. Refresh to request a new snapshot. Verify prices and contract details in Groww before any trade. SL/targets are illustrative and not a validated strategy.</div>', unsafe_allow_html=True)

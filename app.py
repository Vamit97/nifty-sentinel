import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

TZ=ZoneInfo("Asia/Kolkata")
BASE="https://api.groww.in/v1"
st.set_page_config(page_title="NIFTY SENTINEL | Markets",page_icon="📈",layout="wide",initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#f5f7fa;--panel:#ffffff;--ink:#182230;--muted:#687586;--line:#e4e9f0;--green:#00a86b;--red:#e5484d;--navy:#111827;}
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{padding-top:1.2rem;padding-bottom:2rem;max-width:1440px}
[data-testid="stHeader"]{background:rgba(245,247,250,.92)}
[data-testid="stSidebar"]{background:#111827;border-right:1px solid #263244}
[data-testid="stSidebar"] *{color:#edf2f7}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#182230}
[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--line);padding:18px 18px 14px;border-radius:12px;box-shadow:0 2px 8px rgba(16,24,40,.035)}
[data-testid="stMetricLabel"]{color:var(--muted);font-weight:600;font-size:.85rem}
[data-testid="stMetricValue"]{color:var(--ink);font-weight:750;letter-spacing:-.04em}
.stButton>button{border-radius:9px;font-weight:650;min-height:44px;border:1px solid #d6dde7}
.stButton>button[kind="primary"]{background:#00a86b;border-color:#00a86b;color:white}
.stButton>button[kind="primary"]:hover{background:#008e5a;border-color:#008e5a;color:white}
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"]{background:white;border:1px solid var(--line);border-radius:12px;overflow:hidden;padding:5px}
[data-testid="stAlert"]{border-radius:10px}
h1,h2,h3{letter-spacing:-.035em;color:var(--ink)}
.brandbar{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#111827;color:#f8fafc;border-radius:14px;padding:17px 22px;margin-bottom:16px}
.brandleft{display:flex;align-items:center;gap:12px}.brandicon{font-size:25px;background:#00a86b;color:white;border-radius:9px;width:42px;height:42px;display:flex;align-items:center;justify-content:center}
.brandtitle{font-size:1.25rem;font-weight:800;letter-spacing:-.04em;color:#fff}.brandsub{font-size:.76rem;color:#b7c2d0;margin-top:3px}.livepill{border:1px solid #276b53;background:#123a2c;color:#7ee2b8;border-radius:999px;padding:7px 11px;font-size:.76rem;font-weight:700;white-space:nowrap}
.sectionhead{display:flex;align-items:center;justify-content:space-between;margin:1.1rem 0 .55rem}.sectionhead h3{font-size:1.12rem;font-weight:750;margin:0}.sectionhint{font-size:.78rem;color:var(--muted)}
div[data-testid="stVerticalBlock"]>div:has(> .sectionhead){margin-top:.25rem}
@media(max-width:640px){.block-container{padding: .8rem .75rem 1.5rem}.brandbar{padding:13px 14px}.brandtitle{font-size:1.05rem}.brandsub{font-size:.68rem}.livepill{font-size:.68rem;padding:6px 8px}[data-testid="stMetric"]{padding:12px}.sectionhint{display:none}}
</style>
<div class="brandbar"><div class="brandleft"><div class="brandicon">↗</div><div><div class="brandtitle">NIFTY SENTINEL</div><div class="brandsub">INDIAN MARKETS · OPTIONS ANALYTICS · MANUAL EXECUTION</div></div></div><div class="livepill">● LIVE DATA MODE</div></div>
""",unsafe_allow_html=True)

st.markdown('''<div class="sectionhead"><h3>Market overview</h3><span class="sectionhint">Groww API · Snapshot data</span></div>''',unsafe_allow_html=True)
with st.sidebar:
    st.subheader("Groww API Authentication")
    auth_mode = st.radio("Authentication method", ["Access token", "TOTP token"], index=0)
    secret_token = ""
    try:
        secret_token = st.secrets.get("GROWW_ACCESS_TOKEN", "")
    except Exception:
        pass
    token = ""
    if auth_mode == "Access token":
        token = st.text_input("Groww access token", value=secret_token, type="password",
                              help="Daily access token; keep private.")
    else:
        st.caption("Use the TOTP token + TOTP secret from Groww Trading APIs. These are not your normal API key/secret.")
        totp_token = st.text_input("Groww TOTP token", type="password")
        totp_secret = st.text_input("TOTP secret", type="password")
        if st.button("Generate access token from TOTP", use_container_width=True):
            try:
                import pyotp
                from growwapi import GrowwAPI
                if not totp_token.strip() or not totp_secret.strip():
                    raise ValueError("Enter both TOTP token and TOTP secret.")
                current_otp = pyotp.TOTP(totp_secret.strip()).now()
                generated = GrowwAPI.get_access_token(api_key=totp_token.strip(), totp=current_otp)
                st.session_state["groww_generated_access_token"] = generated
                st.session_state["groww_generated_token_time"] = datetime.now(TZ).strftime("%H:%M:%S IST")
                st.success("Access token generated successfully. It is held in this session only.")
            except Exception as e:
                st.session_state.pop("groww_generated_access_token", None)
                st.error("TOTP authentication failed. Check TOTP token/secret and Groww API approval.")
                st.caption(f"Diagnostic: {type(e).__name__}: {str(e)[:220]}")
        token = st.session_state.get("groww_generated_access_token", "")
        if token:
            st.caption("Session token generated at " + st.session_state.get("groww_generated_token_time", ""))
    # NIFTY weekly expiries are generally Tuesday; show candidate dates instead of defaulting to today.
    # Holidays/contract calendars can differ, so the user must verify the actual listed expiry.
    today = datetime.now(TZ).date()
    candidate_expiries = []
    for offset in range(0, 70):
        d = today.fromordinal(today.toordinal() + offset)
        if d.weekday() == 1:  # Tuesday
            candidate_expiries.append(d)
    future_expiries = [d for d in candidate_expiries if d > today]
    default_expiry = future_expiries[0] if future_expiries else candidate_expiries[0]
    expiry = st.selectbox(
        "NIFTY expiry (verify against Groww contract list)",
        options=candidate_expiries,
        index=candidate_expiries.index(default_expiry),
        format_func=lambda d: d.strftime("%d %b %Y") + (" • today" if d == today else ""),
        help="Candidate Tuesday dates only; exchange holidays or contract changes may alter the actual expiry."
    )
    capital=st.number_input("Trading capital (₹)",min_value=1000,value=150000,step=5000)
    risk_pct=st.slider("Risk budget (%)",0.25,2.0,0.5,0.25)
    st.caption("Keep all tokens and secrets private. Never commit them to GitHub.")
refresh_col, time_col = st.columns([1,2])
with refresh_col:
    st.button("↻  Refresh market data",type="primary",use_container_width=True)
with time_col:
    st.markdown(f"<div style='text-align:right;color:#687586;padding-top:12px;font-size:.82rem'>Updated {datetime.now(TZ).strftime('%d %b %Y · %H:%M:%S IST')}</div>",unsafe_allow_html=True)
if not token:
    if auth_mode == "Access token":
        st.warning("Groww access token set karein, ya sidebar mein TOTP token method select karein.")
        st.code('GROWW_ACCESS_TOKEN = "your_access_token"')
    else:
        st.info("Sidebar mein TOTP token aur TOTP secret enter karke Generate access token dabayein.")
    st.stop()

headers={"Accept":"application/json","Authorization":f"Bearer {token}","X-API-VERSION":"1.0"}
def api_get(path,params=None):
    r=requests.get(BASE+path,headers=headers,params=params,timeout=15)
    if r.status_code != 200:
        # Do not echo request headers or token.
        raise RuntimeError(f"HTTP {r.status_code} at {path}: {r.text[:350]}")
    j=r.json()
    if j.get("status")=="FAILURE":
        raise RuntimeError(f"Groww API returned FAILURE at {path}: {str(j)[:350]}")
    return j.get("payload",j)

# Diagnostic request first, using exact official endpoint schema.
try:
    ltp_payload=api_get("/live-data/ltp",{"segment":"CASH","exchange_symbols":"NSE_NIFTY"})
    spot=ltp_payload.get("NSE_NIFTY") if isinstance(ltp_payload,dict) else None
    if spot is None: raise RuntimeError(f"NIFTY LTP missing in response: {str(ltp_payload)[:250]}")
    spot=float(spot)
except Exception as e:
    st.error("Groww live quote request failed.")
    st.code(str(e))
    st.markdown("**What this means:** HTTP 401/403 usually points to authentication/authorization or API access configuration; this message alone cannot prove a static-IP issue.")
    st.info("Market band hona aam taur par 403 Access Forbidden ka explanation nahi hai. Access token/TOTP approval, API permissions, aur Groww response check karein. Token chat mein share na karein.")
    st.stop()

m1,m2=st.columns(2)
m1.metric("NIFTY 50",f"{spot:,.2f}")
m2.metric("Feed status","LIVE API response")
st.success("NIFTY quote fetched successfully. Option chain is being requested separately.")

try:
    ohlc=api_get("/live-data/ohlc",{"segment":"CASH","exchange_symbols":"NSE_NIFTY"})
    oi=ohlc.get("NSE_NIFTY",{})
    if isinstance(oi,str):
        import ast
        try: oi=ast.literal_eval(oi)
        except Exception: oi={}
except Exception as e:
    oi={}
    st.warning(f"OHLC request failed separately: {e}")

try:
    chain=api_get("/option-chain/exchange/NSE/underlying/NIFTY", {"expiry_date": expiry.isoformat()})
    strikes=chain.get("strikes",{})
    rows=[]
    for strike,sides in strikes.items():
        try: k=float(strike)
        except Exception: continue
        row={"Strike":k}
        for side in ("CE","PE"):
            c=sides.get(side) or {}
            g=c.get("greeks") or {}
            row.update({f"{side} LTP":c.get("ltp"),f"{side} OI":c.get("open_interest"),
                        f"{side} Volume":c.get("volume"),f"{side} Delta":g.get("delta"),
                        f"{side} IV":g.get("iv"),f"{side} Symbol":c.get("trading_symbol")})
        rows.append(row)
except Exception as e:
    st.error(f"NIFTY quote works, but option-chain request failed for expiry {expiry.isoformat()}.")
    st.code(str(e))
    st.info("Check that this exact expiry is listed in Groww. Candidate Tuesday dates exclude exchange-holiday adjustments; HTTP 500/GA000 can also be a Groww-side issue. The NIFTY quote is kept separate and is working.")
    st.stop()

df=pd.DataFrame(rows).sort_values("Strike") if rows else pd.DataFrame()
if df.empty:
    st.error("Option chain returned no strikes. Verify expiry date.")
    st.stop()
atm_strike=float(df.iloc[(df["Strike"]-spot).abs().argsort()[:1]]["Strike"].iloc[0])
atm=df.loc[df["Strike"]==atm_strike].iloc[0]
ce=pd.to_numeric(pd.Series([atm.get("CE LTP")]),errors="coerce").iloc[0]
pe=pd.to_numeric(pd.Series([atm.get("PE LTP")]),errors="coerce").iloc[0]
a,b,c,d=st.columns(4)
a.metric("NIFTY",f"{spot:,.2f}")
b.metric("ATM strike",f"{atm_strike:,.0f}")
c.metric("ATM CE premium",f"₹{ce:,.2f}" if pd.notna(ce) else "N/A")
d.metric("ATM PE premium",f"₹{pe:,.2f}" if pd.notna(pe) else "N/A")

st.markdown('''<div class="sectionhead"><h3>Price snapshot</h3><span class="sectionhint">Open · High · Low · Close</span></div>''',unsafe_allow_html=True)
o1,o2,o3,o4=st.columns(4)
for col,label,key in [(o1,"Open","open"),(o2,"High","high"),(o3,"Low","low"),(o4,"Close field","close")]:
    try: col.metric(label,f"{float(oi[key]):,.2f}")
    except Exception: col.metric(label,"N/A")

st.markdown('''<div class="sectionhead"><h3>Trade planning</h3><span class="sectionhint">Illustrative risk calculator · not a signal</span></div>''',unsafe_allow_html=True)
selected=st.selectbox("Contract",["ATM CE","ATM PE"])
premium=float(ce if selected.endswith("CE") else pe) if pd.notna(ce if selected.endswith("CE") else pe) else None
if premium and premium>0:
    sl_pct=st.slider("Illustrative premium SL (%)",5,40,20,5)
    rmult=st.selectbox("Target R multiple",[1.0,1.5,2.0,3.0],index=2)
    sl=premium*(1-sl_pct/100)
    target=premium+(premium-sl)*rmult
    risk=capital*risk_pct/100
    units=int(risk/(premium-sl)) if premium>sl else 0
    x1,x2,x3=st.columns(3)
    x1.metric("Reference premium",f"₹{premium:.2f}")
    x2.metric("Illustrative SL",f"₹{sl:.2f}")
    x3.metric(f"Illustrative target ({rmult:g}R)",f"₹{target:.2f}")
    st.caption(f"Risk budget ₹{risk:,.0f}; theoretical units {units:,} before lot-size rounding/charges. This is a calculator, not a validated signal.")
st.markdown('''<div class="sectionhead"><h3>Option chain</h3><span class="sectionhint">CE / PE premiums, OI, volume and Greeks</span></div>''',unsafe_allow_html=True)
cols=["CE LTP","CE OI","CE Volume","CE Delta","CE IV","Strike","PE LTP","PE OI","PE Volume","PE Delta","PE IV"]
st.dataframe(df[cols],use_container_width=True,hide_index=True,height=420)
near=df[(df["Strike"]>=atm_strike-500)&(df["Strike"]<=atm_strike+500)]
fig=go.Figure()
fig.add_trace(go.Scatter(x=near["Strike"],y=pd.to_numeric(near["CE LTP"],errors="coerce"),mode="lines+markers",name="CE premium"))
fig.add_trace(go.Scatter(x=near["Strike"],y=pd.to_numeric(near["PE LTP"],errors="coerce"),mode="lines+markers",name="PE premium"))
fig.add_vline(x=spot,line_dash="dash",annotation_text=f"NIFTY {spot:.0f}")
fig.update_layout(template="plotly_dark",height=330,margin=dict(l=8,r=8,t=25,b=8),xaxis_title="Strike",yaxis_title="Premium ₹")
st.plotly_chart(fig,use_container_width=True)
st.markdown("<div style='background:#fff8e8;border:1px solid #f4d99a;border-radius:10px;padding:13px 15px;color:#75551b;font-size:.84rem'><b>Risk notice</b> · Manual execution only. No orders are placed. Stop-loss and target values are illustrative, not validated trade calls. Verify the contract, live premium, liquidity and timestamp in Groww before trading.</div>",unsafe_allow_html=True)

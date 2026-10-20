import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

TZ=ZoneInfo("Asia/Kolkata")
BASE="https://api.groww.in/v1"
st.set_page_config(page_title="NIFTY SENTINEL LIVE",page_icon="📈",layout="wide")
st.markdown("""
<style>
.stApp{background:#070d17;color:#edf3ff}
[data-testid="stMetric"]{background:#101b2b;border:1px solid #26364d;padding:14px;border-radius:14px}
section[data-testid="stSidebar"]{background:#0b1422}
</style>""",unsafe_allow_html=True)

st.title("📈 NIFTY SENTINEL")
st.caption("LIVE MARKET MONITOR • OPTION CHAIN • MANUAL EXECUTION")
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
    expiry=st.date_input("NIFTY expiry",value=date.today())
    capital=st.number_input("Trading capital (₹)",min_value=1000,value=150000,step=5000)
    risk_pct=st.slider("Risk budget (%)",0.25,2.0,0.5,0.25)
    st.caption("Keep all tokens and secrets private. Never commit them to GitHub.")
st.button("↻ Refresh live data",type="primary",use_container_width=True)
st.caption("Dashboard time: "+datetime.now(TZ).strftime("%d %b %Y, %H:%M:%S IST"))
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
    chain=api_get(f"/option-chain/exchange/NSE/underlying/NIFTY",{"expiry_date":expiry.isoformat()})
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
    st.error("NIFTY quote works, but option-chain request failed.")
    st.code(str(e))
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

st.subheader("Market OHLC snapshot")
o1,o2,o3,o4=st.columns(4)
for col,label,key in [(o1,"Open","open"),(o2,"High","high"),(o3,"Low","low"),(o4,"Close field","close")]:
    try: col.metric(label,f"{float(oi[key]):,.2f}")
    except Exception: col.metric(label,"N/A")

st.subheader("Trade planning calculator")
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
st.subheader("Option chain")
cols=["CE LTP","CE OI","CE Volume","CE Delta","CE IV","Strike","PE LTP","PE OI","PE Volume","PE Delta","PE IV"]
st.dataframe(df[cols],use_container_width=True,hide_index=True,height=420)
near=df[(df["Strike"]>=atm_strike-500)&(df["Strike"]<=atm_strike+500)]
fig=go.Figure()
fig.add_trace(go.Scatter(x=near["Strike"],y=pd.to_numeric(near["CE LTP"],errors="coerce"),mode="lines+markers",name="CE premium"))
fig.add_trace(go.Scatter(x=near["Strike"],y=pd.to_numeric(near["PE LTP"],errors="coerce"),mode="lines+markers",name="PE premium"))
fig.add_vline(x=spot,line_dash="dash",annotation_text=f"NIFTY {spot:.0f}")
fig.update_layout(template="plotly_dark",height=330,margin=dict(l=8,r=8,t=25,b=8),xaxis_title="Strike",yaxis_title="Premium ₹")
st.plotly_chart(fig,use_container_width=True)
st.warning("No automatic orders. Do not use these illustrative SL/targets as trade calls. Verify quotes, expiry, liquidity and timestamps in Groww before any manual trade.")

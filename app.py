import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="centered")
st.title("📈 NIFTY SENTINEL")
st.caption("Research dashboard • Public data • No broker orders")
st.warning("NIFTY underlying only — this is not an actual CE/PE premium backtest and does not guarantee profits.")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(period, interval):
    import yfinance as yf
    try:
        raw = yf.Ticker("^NSEI").history(period=period, interval=interval, auto_adjust=False)
        if raw is None or raw.empty:
            return pd.DataFrame(), "Public feed returned no candles."
        raw = raw.reset_index()
        if "Datetime" in raw.columns:
            raw = raw.rename(columns={"Datetime":"Date"})
        return raw, None
    except Exception as exc:
        return pd.DataFrame(), f"{type(exc).__name__}: {exc}"

def prepare(raw):
    df=raw.copy()
    rename={}
    for col in df.columns:
        n=str(col).strip().lower()
        if n in ("date","datetime","timestamp","time"): rename[col]="Date"
        elif n in ("open","high","low","close","volume"): rename[col]=n.title()
    df=df.rename(columns=rename)
    req=["Open","High","Low","Close"]
    missing=[x for x in req if x not in df.columns]
    if missing: raise ValueError("Missing columns: "+", ".join(missing))
    for col in ["Open","High","Low","Close","Volume"]:
        if col in df: df[col]=pd.to_numeric(df[col],errors="coerce")
    if "Date" in df:
        df["Date"]=pd.to_datetime(df["Date"],errors="coerce")
        df=df.sort_values("Date").drop_duplicates(subset=["Date"],keep="last")
    df=df.dropna(subset=req).reset_index(drop=True)
    if len(df)<100: raise ValueError(f"Only {len(df)} candles found; need at least 100.")
    c,h,l=df.Close,df.High,df.Low
    df["EMA20"]=c.ewm(span=20,adjust=False).mean()
    df["EMA50"]=c.ewm(span=50,adjust=False).mean()
    change=c.diff()
    gain=change.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-change.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs=gain/loss.replace(0,np.nan)
    df["RSI"]=(100-100/(1+rs)).fillna(50)
    prev=c.shift()
    tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    df["ATR"]=tr.ewm(alpha=1/14,adjust=False).mean()
    df["PriorHigh20"]=h.shift(1).rolling(20).max()
    df["PriorLow20"]=l.shift(1).rolling(20).min()
    return df

def get_signal(row):
    names=["Close","EMA20","EMA50","RSI","PriorHigh20","PriorLow20"]
    if any(pd.isna(row[n]) for n in names): return 0
    if row.Close>row.EMA20>row.EMA50 and row.Close>row.PriorHigh20 and 52<=row.RSI<=72: return 1
    if row.Close<row.EMA20<row.EMA50 and row.Close<row.PriorLow20 and 28<=row.RSI<=48: return -1
    return 0

def backtest(df,start,end,stop_atr,target_r,cost):
    rows=[]
    start=max(51,int(start)); end=min(int(end),len(df)-1)
    i=start
    while i<end:
        sig=get_signal(df.iloc[i]); atr=df.iloc[i].ATR
        if sig==0 or pd.isna(atr) or atr<=0:
            i+=1; continue
        ei=i+1
        if ei>end: break
        entry=float(df.iloc[ei].Open); risk=float(atr*stop_atr)
        if not np.isfinite(entry) or risk<=0:
            i+=1; continue
        sl=entry-sig*risk; tgt=entry+sig*risk*target_r
        exit_price=float(df.iloc[end].Close); exit_i=end
        reason="Window-end mark-to-market (unfinished)"
        completed=False
        for j in range(ei,end+1):
            bar=df.iloc[j]
            stop_hit=(float(bar.Low)<=sl) if sig==1 else (float(bar.High)>=sl)
            target_hit=(float(bar.High)>=tgt) if sig==1 else (float(bar.Low)<=tgt)
            if stop_hit and target_hit:
                exit_price,exit_i,reason,completed=sl,j,"Stop-loss (same-candle conservative rule)",True; break
            if stop_hit:
                exit_price,exit_i,reason,completed=sl,j,"Stop-loss",True; break
            if target_hit:
                exit_price,exit_i,reason,completed=tgt,j,"Target",True; break
        net=sig*(exit_price-entry)-cost
        rows.append({"Signal date":df.iloc[i].Date if "Date" in df else i,
                     "Entry date":df.iloc[ei].Date if "Date" in df else ei,
                     "Side":"LONG underlying" if sig==1 else "SHORT underlying",
                     "Entry":entry,"Stop":sl,"Target":tgt,"Exit":exit_price,
                     "Exit reason":reason,"Completed by SL/target":completed,
                     "Net points after assumed costs":net,
                     "R multiple after costs":net/risk,"Bars held":exit_i-ei+1})
        i=exit_i+1
    return pd.DataFrame(rows)

def summarize(trades):
    if trades.empty: return None
    pnl=trades["Net points after assumed costs"].astype(float)
    win=pnl>0
    gross_profit=float(pnl[pnl>0].sum())
    gross_loss=float(-pnl[pnl<0].sum())
    equity=pnl.cumsum()
    peak=equity.cummax().clip(lower=0)
    drawdown=float((equity-peak).min())
    # Explicit keys avoid KeyError on empty/partially populated frames.
    avg_r=float(trades["R multiple after costs"].mean()) if "R multiple after costs" in trades.columns else float("nan")
    return {"n":int(len(trades)),
            "completed":int(trades["Completed by SL/target"].sum()) if "Completed by SL/target" in trades.columns else 0,
            "win_rate":float(win.mean()*100),
            "net_points":float(pnl.sum()),
            "profit_factor":gross_profit/gross_loss if gross_loss>0 else (float("inf") if gross_profit>0 else 0.0),
            "avg_r":avg_r,"max_drawdown":drawdown}

with st.sidebar:
    st.header("Data settings")
    interval=st.selectbox("Candle interval",["15m","30m","1d"],index=0)
    periods={"15m":["5d","1mo"],"30m":["5d","1mo"],"1d":["6mo","1y","2y","5y"]}
    period=st.selectbox("History",periods[interval],index=len(periods[interval])-1)
    st.header("Backtest assumptions")
    stop_atr=st.selectbox("Stop distance (ATR)",[0.75,1.0,1.25,1.5],index=1)
    target_r=st.selectbox("Target (R)",[1.0,1.5,2.0,2.5,3.0],index=2)
    cost=st.number_input("Assumed round-trip cost (index points)",min_value=0.0,value=2.0,step=0.5)
    st.caption("This is an illustrative index-point deduction, not actual option trading costs.")

upload=st.file_uploader("Optional: upload candle CSV",type=["csv"],help="Required: Open, High, Low, Close. Date optional.")
if st.button("Refresh market data",type="primary"): st.cache_data.clear()
try:
    if upload is not None:
        raw=pd.read_csv(upload); source="Uploaded CSV"
    else:
        with st.spinner("Fetching NIFTY candles..."):
            raw,error=fetch_data(period,interval)
        if raw.empty:
            st.error(f"Market data unavailable: {error}")
            st.info("Try Daily + 1y history, or upload CSV. No signal without data.")
            st.stop()
        source=f"Public feed • {period}/{interval}"
    df=prepare(raw)
except Exception as exc:
    st.error(f"Data error: {type(exc).__name__}: {exc}")
    st.info("CSV needs at least 100 valid candles and Open, High, Low, Close.")
    st.stop()

last,prev=df.iloc[-1],df.iloc[-2]
if "Date" in df and pd.notna(last.Date):
    try:
        stamp=pd.Timestamp(last.Date)
        now=pd.Timestamp.now(tz=stamp.tz) if stamp.tzinfo else pd.Timestamp.now()
        if now-stamp>pd.Timedelta(days=3): st.warning("Latest candle may be stale. Verify timestamp before interpreting signal.")
    except Exception: pass
sig=get_signal(last)
label="BULLISH BREAKOUT" if sig==1 else ("BEARISH BREAKDOWN" if sig==-1 else "NO TRADE")
a,b,c=st.columns(3)
a.metric("NIFTY close",f"{float(last.Close):,.2f}",f"{float(last.Close-prev.Close):+.2f}")
b.metric("Signal",label)
c.metric("RSI",f"{float(last.RSI):.1f}")
st.caption(f"Source: {source} • Latest candle: {last.Date if 'Date' in df else 'date unavailable'}")
if sig:
    entry=float(last.Close); risk=float(last.ATR)*stop_atr
    a,b,c=st.columns(3)
    a.metric("Underlying reference",f"{entry:,.2f}")
    b.metric("Underlying stop",f"{entry-sig*risk:,.2f}")
    c.metric("Underlying target",f"{entry+sig*risk*target_r:,.2f}")
else: st.info("NO TRADE — wait for all conditions; do not force an entry.")
st.caption("Underlying levels only, NOT option premiums. No live option chain, IV, Greeks, spreads or broker execution.")

with st.expander("Indicators and recent candles"):
    cols=[x for x in ["Date","Open","High","Low","Close","Volume","EMA20","EMA50","RSI","ATR","PriorHigh20","PriorLow20"] if x in df]
    st.dataframe(df[cols].tail(30),use_container_width=True,hide_index=True)
    if "Date" in df: st.line_chart(df.set_index("Date")["Close"].tail(200))
    else: st.line_chart(df["Close"].tail(200))

st.subheader("Historical test")
st.caption("Chronological 70/30 split. Entry is next candle open; one position at a time. Window-end trades are marked unfinished. Same-candle SL/target assumes SL first.")
split=int(len(df)*0.70)
for title,start,end,key in [("Development window (first 70%)",51,split-1,"dev"),
                            ("Out-of-sample window (last 30%)",max(51,split-1),len(df)-1,"oos")]:
    trades=backtest(df,start,end,stop_atr,target_r,cost) if end>start else pd.DataFrame()
    st.markdown(f"**{title}**")
    s=summarize(trades)
    if s is None:
        st.info("No qualifying trades in this window."); continue
    a,b,c,d=st.columns(4)
    a.metric("Trades",str(s["n"]),help=f"{s['completed']} exited by SL/target; others marked unfinished.")
    b.metric("Win rate",f"{s['win_rate']:.1f}%")
    c.metric("Net points*",f"{s['net_points']:.1f}")
    d.metric("Profit factor*",f"{s['profit_factor']:.2f}" if np.isfinite(s["profit_factor"]) else "∞")
    st.write(f"Average R*: **{s['avg_r']:.2f}** · Max drawdown*: **{s['max_drawdown']:.1f} points** · SL/target exits: **{s['completed']}**")
    if key=="oos":
        if s["n"]<20: st.warning("Too few out-of-sample trades (<20) for a reliable conclusion. Keep paper-testing.")
        elif s["net_points"]<=0 or s["profit_factor"]<=1: st.warning("Out-of-sample result is not positive under these assumptions. Do not use live.")
        else: st.info("Positive in this sample only; continue paper testing. Not proof of future profitability.")
    st.dataframe(trades,use_container_width=True,hide_index=True)
    st.download_button(f"Download {key.upper()} trades CSV",trades.to_csv(index=False).encode("utf-8"),f"nifty_sentinel_{key}_trades.csv","text/csv",key=f"dl_{key}")
st.download_button("Download analysed candles CSV",df.to_csv(index=False).encode("utf-8"),"nifty_sentinel_candles.csv","text/csv")
st.caption("Research prototype only. Index points are not rupee P&L. No orders are placed. Never upload API keys to a public repository.")

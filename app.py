import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="centered")
st.title("📈 NIFTY SENTINEL")
st.caption("Research dashboard • Free public data • No broker orders")
st.warning("Research only. This app tests NIFTY underlying candles, not CE/PE option premiums. Index points are not rupee P&L.")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(period, interval):
    import yfinance as yf
    try:
        raw=yf.Ticker("^NSEI").history(period=period, interval=interval, auto_adjust=False)
        if raw is None or raw.empty: return pd.DataFrame(), "Public feed returned no candles."
        raw=raw.reset_index()
        if "Datetime" in raw.columns: raw=raw.rename(columns={"Datetime":"Date"})
        return raw,None
    except Exception as e: return pd.DataFrame(),f"{type(e).__name__}: {e}"

def prepare(raw):
    df=raw.copy()
    rename={}
    for col in df.columns:
        n=str(col).strip().lower()
        if n in ("date","datetime","timestamp","time"): rename[col]="Date"
        elif n in ("open","high","low","close","volume"): rename[col]=n.title()
    df=df.rename(columns=rename)
    required=["Open","High","Low","Close"]
    missing=[x for x in required if x not in df.columns]
    if missing: raise ValueError("Missing columns: "+", ".join(missing))
    for c in ["Open","High","Low","Close","Volume"]:
        if c in df: df[c]=pd.to_numeric(df[c],errors="coerce")
    if "Date" in df:
        df["Date"]=pd.to_datetime(df["Date"],errors="coerce")
        df=df.dropna(subset=["Date"]).sort_values("Date").drop_duplicates("Date",keep="last")
    df=df.dropna(subset=required).reset_index(drop=True)
    if len(df)<100: raise ValueError(f"Only {len(df)} valid candles; at least 100 are needed.")
    c,h,l=df.Close,df.High,df.Low
    df["EMA20"]=c.ewm(span=20,adjust=False).mean()
    df["EMA50"]=c.ewm(span=50,adjust=False).mean()
    # Wilder-style RSI with explicit edge handling.
    change=c.diff()
    gain=change.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    loss=(-change.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rs=gain/loss.replace(0,np.nan)
    rsi=100-100/(1+rs)
    rsi=rsi.mask((loss==0)&(gain>0),100)
    rsi=rsi.mask((gain==0)&(loss>0),0)
    df["RSI"]=rsi.fillna(50)
    prev=c.shift()
    tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    df["ATR"]=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    df["PriorHigh20"]=h.shift(1).rolling(20,min_periods=20).max()
    df["PriorLow20"]=l.shift(1).rolling(20,min_periods=20).min()
    # Regime context: normalized EMA separation and ATR as a percentage of price.
    df["TrendStrength"]=(df["EMA20"]-df["EMA50"]).abs()/df["ATR"].replace(0,np.nan)
    df["ATRpct"]=100*df["ATR"]/df["Close"]
    return df

def get_signal(row, mode):
    required=["Close","EMA20","EMA50","RSI","ATR"]
    if any(pd.isna(row[x]) for x in required) or row.ATR<=0: return 0
    if mode=="Breakout (baseline)":
        if pd.isna(row.PriorHigh20) or pd.isna(row.PriorLow20): return 0
        if row.Close>row.EMA20>row.EMA50 and row.Close>row.PriorHigh20 and 52<=row.RSI<=72: return 1
        if row.Close<row.EMA20<row.EMA50 and row.Close<row.PriorLow20 and 28<=row.RSI<=48: return -1
    elif mode=="Trend pullback (research)":
        # Reclaim/reject EMA20 in direction of the broader EMA50 trend.
        if row.EMA20>row.EMA50 and row.Close>row.EMA50 and 45<=row.RSI<=62 and row.Close>=row.EMA20: return 1
        if row.EMA20<row.EMA50 and row.Close<row.EMA50 and 38<=row.RSI<=55 and row.Close<=row.EMA20: return -1
    return 0

def run_backtest(df, start, end, mode, stop_atr, target_r, cost_points, max_hold):
    # Window-local: signal on close, enter next candle open. End-of-window open positions are marked,
    # explicitly not counted as completed SL/target exits. If SL and target hit in same bar, SL first.
    out=[]
    start=max(60,int(start)); end=min(int(end),len(df)-1)
    i=start
    while i<end:
        sig=get_signal(df.iloc[i],mode)
        atr=df.iloc[i]["ATR"]
        if sig==0 or pd.isna(atr) or atr<=0:
            i+=1; continue
        ei=i+1
        if ei>end: break
        entry=float(df.iloc[ei]["Open"]); risk=float(atr*stop_atr)
        if not np.isfinite(entry) or risk<=0:
            i+=1; continue
        sl=entry-sig*risk; target=entry+sig*risk*target_r
        last_bar=min(end,ei+max_hold-1)
        exit_price=float(df.iloc[last_bar]["Close"]); xi=last_bar
        reason="Max hold / window mark-to-market"; completed=False
        for j in range(ei,last_bar+1):
            bar=df.iloc[j]
            stop_hit=(float(bar.Low)<=sl) if sig==1 else (float(bar.High)>=sl)
            target_hit=(float(bar.High)>=target) if sig==1 else (float(bar.Low)<=target)
            if stop_hit and target_hit:
                exit_price,xi,reason,completed=sl,j,"Stop-loss (conservative same-bar rule)",True; break
            if stop_hit:
                exit_price,xi,reason,completed=sl,j,"Stop-loss",True; break
            if target_hit:
                exit_price,xi,reason,completed=target,j,"Target",True; break
        if not completed and xi<end and xi==last_bar and (xi-ei+1)>=max_hold:
            reason="Time exit at candle close"; completed=True
        net=sig*(exit_price-entry)-cost_points
        out.append({
            "Signal date":df.iloc[i]["Date"] if "Date" in df else i,
            "Entry date":df.iloc[ei]["Date"] if "Date" in df else ei,
            "Side":"LONG underlying" if sig==1 else "SHORT underlying",
            "Entry":entry,"Stop":sl,"Target":target,"Exit":exit_price,
            "Exit reason":reason,"Completed trade":completed,
            "Net index points after assumed cost":net,
            "R multiple after assumed cost":net/risk,
            "Bars held":xi-ei+1
        })
        i=xi+1
    return pd.DataFrame(out)

def summarize(trades):
    if trades.empty: return None
    # Report completed trades separately from end-of-window marks.
    comp=trades[trades["Completed trade"]==True].copy()
    p=comp["Net index points after assumed cost"].astype(float)
    gp=float(p[p>0].sum()); gl=float(-p[p<0].sum())
    eq=p.cumsum()
    peak=pd.concat([pd.Series([0.0]),eq.reset_index(drop=True)],ignore_index=True).cummax().iloc[1:].reset_index(drop=True)
    dd=float((eq.reset_index(drop=True)-peak).min()) if len(eq) else 0.0
    all_net=float(trades["Net index points after assumed cost"].sum())
    return {
        "total":len(trades),"completed":len(comp),"unfinished":len(trades)-len(comp),
        "win_rate":float((p>0).mean()*100) if len(p) else float("nan"),
        "net_completed":float(p.sum()) if len(p) else 0.0,
        "net_including_marks":all_net,
        "pf":gp/gl if gl>0 else (float("inf") if gp>0 else 0.0),
        "avg_r":float(comp["R multiple after assumed cost"].mean()) if len(comp) else float("nan"),
        "dd":dd
    }

with st.sidebar:
    st.header("Data")
    interval=st.selectbox("Candle interval",["15m","30m","1d"],index=0)
    opts={"15m":["5d","1mo"],"30m":["5d","1mo"],"1d":["6mo","1y","2y","5y"]}
    period=st.selectbox("History",opts[interval],index=len(opts[interval])-1)
    st.header("Research setup")
    mode=st.selectbox("Strategy to test",["Breakout (baseline)","Trend pullback (research)"])
    stop_atr=st.selectbox("Stop distance (ATR)",[0.75,1.0,1.25,1.5],index=1)
    target_r=st.selectbox("Target (R)",[1.0,1.5,2.0,2.5,3.0],index=2)
    max_hold=st.selectbox("Maximum holding candles",[4,8,12,20],index=1)
    cost_points=st.number_input("Assumed cost per trade (index points)",min_value=0.0,value=2.0,step=0.5)
    st.caption("Illustrative index-point deduction only; not actual options costs.")

upload=st.file_uploader("Optional candle CSV",type=["csv"],help="Open, High, Low, Close required; Date optional.")
if st.button("Refresh market data",type="primary"): st.cache_data.clear()
try:
    if upload is not None:
        raw=pd.read_csv(upload); source="Uploaded CSV"
    else:
        with st.spinner("Fetching public NIFTY candles..."):
            raw,error=fetch_data(period,interval)
        if raw.empty:
            st.error(f"Market data unavailable: {error}")
            st.info("Try Daily + 1y history, or upload a candle CSV. No signal is produced without data.")
            st.stop()
        source=f"Public feed • {period}/{interval}"
    df=prepare(raw)
except Exception as e:
    st.error(f"Data error: {type(e).__name__}: {e}")
    st.info("CSV must have at least 100 valid candles and Open, High, Low, Close.")
    st.stop()

last,prev=df.iloc[-1],df.iloc[-2]
if "Date" in df and pd.notna(last.Date):
    try:
        stamp=pd.Timestamp(last.Date); now=pd.Timestamp.now(tz=stamp.tz) if stamp.tzinfo else pd.Timestamp.now()
        if now-stamp>pd.Timedelta(days=3): st.warning("Latest candle may be stale. Verify its timestamp.")
    except Exception: pass
sig=get_signal(last,mode)
label="BULLISH SETUP" if sig==1 else ("BEARISH SETUP" if sig==-1 else "NO TRADE")
a,b,c=st.columns(3)
a.metric("NIFTY close",f"{float(last.Close):,.2f}",f"{float(last.Close-prev.Close):+.2f}")
b.metric("Signal",label)
c.metric("RSI",f"{float(last.RSI):.1f}")
st.caption(f"Source: {source} • Latest candle: {last.Date if 'Date' in df else 'date unavailable'}")
if sig:
    ref=float(last.Close); risk=float(last.ATR)*stop_atr
    a,b,c=st.columns(3)
    a.metric("Underlying reference",f"{ref:,.2f}")
    b.metric("Underlying stop",f"{ref-sig*risk:,.2f}")
    c.metric("Underlying target",f"{ref+sig*risk*target_r:,.2f}")
else: st.info("NO TRADE — wait for the setup; do not force an entry.")
st.caption("Levels are NIFTY underlying points, not option premiums. No live option-chain, IV, Greeks or broker execution.")

with st.expander("Indicators and recent candles"):
    cols=[c for c in ["Date","Open","High","Low","Close","Volume","EMA20","EMA50","RSI","ATR","PriorHigh20","PriorLow20","TrendStrength","ATRpct"] if c in df]
    st.dataframe(df[cols].tail(30),use_container_width=True,hide_index=True)
    if "Date" in df: st.line_chart(df.set_index("Date")["Close"].tail(200))
    else: st.line_chart(df["Close"].tail(200))

st.subheader("Chronological backtest")
st.caption("70/30 chronological split. The development and out-of-sample windows do not share a signal candle. Entry is next candle open. Only one position at a time. Completed trades and unfinished window-end marks are reported separately. Same-candle SL/target assumes SL first.")
split=int(len(df)*0.70)
for title,start,end,key in [("Development window (first 70%)",60,split-1,"dev"),
                            ("Out-of-sample window (last 30%)",split,len(df)-1,"oos")]:
    trades=run_backtest(df,start,end,mode,stop_atr,target_r,cost_points,max_hold) if end>start else pd.DataFrame()
    st.markdown(f"**{title}**")
    s=summarize(trades)
    if s is None:
        st.info("No qualifying trades in this window."); continue
    a,b,c,d=st.columns(4)
    a.metric("Total setups",str(s["total"]))
    b.metric("Completed",str(s["completed"]))
    c.metric("Win rate (completed)",f"{s['win_rate']:.1f}%" if np.isfinite(s["win_rate"]) else "N/A")
    d.metric("Profit factor*",f"{s['pf']:.2f}" if np.isfinite(s["pf"]) else "∞")
    st.write(f"**Completed-trade net:** {s['net_completed']:.1f} points · **Net incl. unfinished marks:** {s['net_including_marks']:.1f} points · **Average R:** {s['avg_r']:.2f} · **Max completed-trade drawdown:** {s['dd']:.1f} points · **Unfinished:** {s['unfinished']}")
    if key=="oos":
        if s["completed"]<20: st.warning("Fewer than 20 completed out-of-sample trades: evidence is insufficient. Continue paper testing.")
        elif s["net_completed"]<=0 or s["pf"]<=1: st.warning("Out-of-sample result is not positive under these assumptions. Do not use live.")
        else: st.info("Positive in this sample only. It is not proof of future profitability.")
    st.dataframe(trades,use_container_width=True,hide_index=True)
    st.download_button(f"Download {key.upper()} trade log",trades.to_csv(index=False).encode("utf-8"),f"nifty_sentinel_{key}_trades.csv","text/csv",key=f"dl_{key}")
st.download_button("Download analysed candles CSV",df.to_csv(index=False).encode("utf-8"),"nifty_sentinel_candles.csv","text/csv")
st.caption("Research prototype only. No orders are placed. Actual options P&L requires historical option premiums and realistic costs. Never put API keys in a public repo.")

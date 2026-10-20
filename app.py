import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="wide")
st.title("📈 NIFTY SENTINEL — Free Research Dashboard")
st.caption("Manual signals only • Research/paper use • No broker orders")

st.warning(
    "This dashboard analyses NIFTY underlying candles, not option premiums or a live option chain. "
    "Public data may be delayed/unavailable. Do not trade from this output alone."
)

with st.sidebar:
    st.header("Settings")
    interval = st.selectbox("Candle interval", ["5m", "15m", "30m", "1d"], index=1)
    # Yahoo Finance intraday retention is limited; use compatible defaults.
    default_period = "5d" if interval in ["5m", "15m", "30m"] else "1y"
    periods = ["5d", "1mo", "3mo", "6mo", "1y"]
    period = st.selectbox("History", periods, index=periods.index(default_period))
    if interval in ["5m", "15m", "30m"] and period not in ["5d", "1mo"]:
        st.info("Intraday history is limited on public feeds. Using 1mo maximum for this request.")
        period = "1mo"
    st.markdown("---")
    capital = st.number_input("Capital (₹)", min_value=1000, value=150000, step=5000)
    risk_pct = st.number_input("Planned risk per trade (%)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
    rr = st.selectbox("Target risk/reward", [1.0, 1.5, 2.0, 2.5, 3.0], index=2)

uploaded = st.file_uploader("Optional: upload candle CSV (Date, Open, High, Low, Close, Volume)", type=["csv"])
if st.button("🔄 Refresh market data", type="primary"):
    st.cache_data.clear()

@st.cache_data(ttl=300, show_spinner=False)
def get_yahoo(period, interval):
    import yfinance as yf
    ticker = yf.Ticker("^NSEI")
    data = ticker.history(period=period, interval=interval, auto_adjust=False, raise_errors=True)
    if data is None or data.empty:
        return pd.DataFrame(), "Yahoo Finance returned an empty dataset."
    data = data.reset_index()
    if "Datetime" in data.columns:
        data = data.rename(columns={"Datetime": "Date"})
    return data, None

def prepare(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    mapping = {}
    for c in df.columns:
        lc = c.lower()
        if lc in ["datetime", "timestamp", "time", "date"]:
            mapping[c] = "Date"
        elif lc in ["open", "high", "low", "close", "volume"]:
            mapping[c] = lc.title()
    df = df.rename(columns=mapping)
    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("CSV columns missing: " + ", ".join(missing))
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Date" in df:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
    df = df.dropna(subset=required).reset_index(drop=True)
    if len(df) < 30:
        raise ValueError(f"Only {len(df)} valid candles found. At least 30 are needed.")
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = (100 - 100 / (1 + rs)).fillna(50)
    df["VWAP"] = np.nan
    if "Volume" in df and df["Volume"].fillna(0).sum() > 0:
        typical = (df["High"] + df["Low"] + df["Close"]) / 3
        if "Date" in df and df["Date"].notna().any():
            days = df["Date"].dt.date
            pv = typical * df["Volume"].fillna(0)
            df["VWAP"] = pv.groupby(days).cumsum() / df["Volume"].fillna(0).groupby(days).cumsum().replace(0, np.nan)
        else:
            df["VWAP"] = (typical * df["Volume"].fillna(0)).cumsum() / df["Volume"].fillna(0).cumsum().replace(0, np.nan)
    tr = pd.concat([df["High"]-df["Low"], (df["High"]-df["Close"].shift()).abs(), (df["Low"]-df["Close"].shift()).abs()], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()
    return df

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        source = "Uploaded CSV"
        error = None
    else:
        with st.spinner("Fetching public NIFTY data..."):
            raw, error = get_yahoo(period, interval)
        source = f"Yahoo Finance public feed (^NSEI), {period}/{interval}"
    if error:
        st.error("Market data fetch failed: " + error)
        st.info("Try changing interval to 1d and history to 1y, then press Refresh. If that also fails, public feed access may be blocked; upload a candle CSV instead.")
        st.stop()
    if raw.empty:
        st.error("No market data returned. Try 1d interval + 1y history or upload a candle CSV.")
        st.stop()
    df = prepare(raw)
except Exception as e:
    st.error(f"Data/processing error: {type(e).__name__}: {e}")
    st.info("Try 1d interval + 1y history. If the public feed is unavailable, upload a CSV with Date, Open, High, Low, Close, Volume.")
    st.stop()

last, prev = df.iloc[-1], df.iloc[-2]
close = float(last["Close"]); ema9 = float(last["EMA9"]); ema21 = float(last["EMA21"]); rsi = float(last["RSI"])
vwap = last["VWAP"]; atr = float(last["ATR14"]) if pd.notna(last["ATR14"]) else max(close*0.002, 1)
bull = close > ema9 > ema21 and 52 <= rsi <= 68
bear = close < ema9 < ema21 and 32 <= rsi <= 48
if pd.notna(vwap):
    bull = bull and close >= float(vwap)
    bear = bear and close <= float(vwap)
if bull:
    bias, direction = "BULLISH SETUP", "CE candidate"
    entry, sl, target = close, close-atr, close+atr*rr
elif bear:
    bias, direction = "BEARISH SETUP", "PE candidate"
    entry, sl, target = close, close+atr, close-atr*rr
else:
    bias, direction = "NO TRADE", "NONE"
    entry = sl = target = np.nan

st.caption(f"Source: {source} • Latest candle: {last['Date'] if 'Date' in df else 'unknown'}")
a,b,c,d = st.columns(4)
a.metric("NIFTY close", f"{close:,.2f}", f"{close-float(prev['Close']):+.2f} vs previous candle")
b.metric("Signal", bias)
c.metric("RSI(14)", f"{rsi:.1f}")
d.metric("ATR(14)", f"{atr:.2f}")
st.subheader("Signal (underlying levels, NOT option premium)")
a,b,c,d = st.columns(4)
a.metric("Direction", direction)
b.metric("Entry", f"{entry:,.2f}" if np.isfinite(entry) else "—")
c.metric("Stop-loss", f"{sl:,.2f}" if np.isfinite(sl) else "—")
d.metric(f"Target ({rr:g}R)", f"{target:,.2f}" if np.isfinite(target) else "—")
st.write(f"Illustrative planned risk budget: ₹{capital*risk_pct/100:,.0f}. This is not a lot-size recommendation or guaranteed maximum loss.")
cols = [x for x in ["Date","Open","High","Low","Close","Volume","EMA9","EMA21","RSI","VWAP","ATR14"] if x in df]
st.subheader("Recent candles")
st.dataframe(df[cols].tail(30), use_container_width=True, hide_index=True)
if "Date" in df:
    st.line_chart(df.set_index("Date")["Close"].tail(150))
else:
    st.line_chart(df["Close"].tail(150))

st.subheader("Simple underlying-candle diagnostic backtest")
st.caption("Educational only: next-candle underlying returns, not option-premium P&L. Excludes costs, slippage, taxes and realistic fills.")
bt = df.copy()
bt["long"] = (bt["Close"] > bt["EMA9"]) & (bt["EMA9"] > bt["EMA21"]) & bt["RSI"].between(52,68)
bt["short"] = (bt["Close"] < bt["EMA9"]) & (bt["EMA9"] < bt["EMA21"]) & bt["RSI"].between(32,48)
if bt["VWAP"].notna().any():
    bt["long"] &= bt["Close"] >= bt["VWAP"]
    bt["short"] &= bt["Close"] <= bt["VWAP"]
bt["position"] = np.select([bt["long"],bt["short"]],[1,-1],default=0)
bt["next_return"] = bt["Close"].shift(-1)/bt["Close"]-1
bt["strategy_return"] = bt["position"]*bt["next_return"]
trades = bt[bt["position"] != 0]
if trades.empty:
    st.info("No signals in this sample. This does not prove the strategy is good or bad.")
else:
    n=len(trades); wins=int((trades["strategy_return"]>0).sum())
    ret=(1+trades["strategy_return"].fillna(0)).prod()-1
    x,y,z=st.columns(3); x.metric("Signal candles",str(n)); y.metric("Next-candle win rate",f"{wins/n*100:.1f}%"); z.metric("Rough compounded underlying return",f"{ret*100:.2f}%")
    st.dataframe(trades[[x for x in ["Date","Close","position","next_return","strategy_return"] if x in trades]].tail(50),use_container_width=True,hide_index=True)
st.download_button("Download analysed candles CSV", df.to_csv(index=False).encode("utf-8"), "nifty_sentinel_analysis.csv", "text/csv")
st.caption("No orders are placed. Public data may be delayed or fail. Verify independently before any financial decision.")

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="wide")

st.title("📈 NIFTY SENTINEL — Free Research Dashboard")
st.caption("Manual signals only • Paper/research use • Not an automated broker or verified profitable strategy")

st.warning(
    "Market data may be delayed, incomplete, or unavailable. This dashboard analyses NIFTY underlying candles, "
    "not option premiums or a live option chain. Do not place a trade based on this output alone."
)

with st.sidebar:
    st.header("Settings")
    period = st.selectbox("History", ["5d", "1mo", "3mo", "6mo", "1y"], index=2)
    interval = st.selectbox("Candle interval", ["5m", "15m", "30m", "1d"], index=1)
    st.markdown("---")
    st.write("**Default risk guardrails (illustrative)**")
    capital = st.number_input("Capital (₹)", min_value=1000, value=150000, step=5000)
    risk_pct = st.number_input("Planned risk per trade (%)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
    rr = st.selectbox("Target risk/reward", [1.0, 1.5, 2.0, 2.5, 3.0], index=2)
    st.caption("Risk controls do not guarantee that losses will stay within these amounts, especially with options.")

uploaded = st.file_uploader("Optional: upload candle CSV (columns: Date, Open, High, Low, Close, Volume)", type=["csv"])
refresh = st.button("🔄 Refresh market data", type="primary")

@st.cache_data(ttl=300, show_spinner=False)
def get_yahoo(period, interval):
    import yfinance as yf
    ticker = yf.Ticker("^NSEI")
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    # Normalize column names
    if "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    if "Date" not in df.columns and "index" in df.columns:
        df = df.rename(columns={"index": "Date"})
    return df

def prepare(df):
    df = df.copy()
    df.columns = [str(c).strip().title() for c in df.columns]
    # normalize common names
    rename = {}
    for c in df.columns:
        low = c.lower()
        if low in ["datetime", "timestamp", "time", "date"]:
            rename[c] = "Date"
        elif low in ["open", "high", "low", "close", "volume"]:
            rename[c] = low.title()
    df = df.rename(columns=rename)
    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("CSV mein required columns missing hain: " + ", ".join(missing))
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).reset_index(drop=True)
    if len(df) < 30:
        raise ValueError("Kam se kam 30 candles chahiye. Zyada historical data upload karo.")
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = (100 - (100 / (1 + rs))).fillna(50)
    if "Volume" in df.columns and df["Volume"].fillna(0).sum() > 0:
        typical = (df["High"] + df["Low"] + df["Close"]) / 3
        # Intraday VWAP resets daily where dates are available; fallback cumulative VWAP otherwise.
        if "Date" in df.columns:
            day = df["Date"].dt.date
            pv = typical * df["Volume"].fillna(0)
            df["VWAP"] = pv.groupby(day).cumsum() / df["Volume"].fillna(0).groupby(day).cumsum().replace(0, np.nan)
        else:
            df["VWAP"] = (typical * df["Volume"].fillna(0)).cumsum() / df["Volume"].fillna(0).cumsum().replace(0, np.nan)
    else:
        df["VWAP"] = np.nan
    df["PrevHigh20"] = df["High"].shift(1).rolling(20).max()
    df["PrevLow20"] = df["Low"].shift(1).rolling(20).min()
    return df

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        data_source = "Uploaded CSV"
    else:
        with st.spinner("Free public market data fetch kar rahe hain..."):
            raw = get_yahoo(period, interval)
        data_source = "Yahoo Finance public feed (may be delayed/unofficial)"
    if raw.empty:
        st.error("Market data fetch nahi hua. Refresh karo ya candle CSV upload karo.")
        st.stop()
    df = prepare(raw)
except Exception as e:
    st.error(f"Data/processing issue: {e}")
    st.info("Alternative: CSV upload karo jisme Date, Open, High, Low, Close, Volume columns hon.")
    st.stop()

last = df.iloc[-1]
prev = df.iloc[-2]
close = float(last["Close"])
ema9 = float(last["EMA9"])
ema21 = float(last["EMA21"])
rsi = float(last["RSI"])
vwap = last["VWAP"]
latest_time = last["Date"] if "Date" in df.columns else "Timestamp unavailable"

# Conservative rule-based directional candidate. It intentionally does not force a trade.
bull = close > ema9 > ema21 and 52 <= rsi <= 68
bear = close < ema9 < ema21 and 32 <= rsi <= 48
if pd.notna(vwap):
    bull = bull and close >= float(vwap)
    bear = bear and close <= float(vwap)
if bull:
    bias, direction = "BULLISH SETUP", "CE candidate"
elif bear:
    bias, direction = "BEARISH SETUP", "PE candidate"
else:
    bias, direction = "NO TRADE", "NONE"

# Illustrative underlying levels based on ATR; these are NOT option premium levels.
tr = pd.concat([
    df["High"] - df["Low"],
    (df["High"] - df["Close"].shift()).abs(),
    (df["Low"] - df["Close"].shift()).abs()
], axis=1).max(axis=1)
atr = float(tr.rolling(14).mean().iloc[-1]) if len(df) >= 14 else np.nan
if not np.isfinite(atr) or atr <= 0:
    atr = max(close * 0.002, 1.0)
if direction == "CE candidate":
    entry, sl = close, close - atr
    target = close + atr * rr
elif direction == "PE candidate":
    entry, sl = close, close + atr
    target = close - atr * rr
else:
    entry = sl = target = np.nan

risk_rupees = capital * (risk_pct / 100)
st.caption(f"Data source: {data_source} • Latest candle: {latest_time}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY close", f"{close:,.2f}", f"{close-float(prev['Close']):+.2f} vs prior candle")
m2.metric("Signal", bias)
m3.metric("RSI(14)", f"{rsi:.1f}")
m4.metric("ATR(14)", f"{atr:.2f}")

st.subheader("Signal card")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Direction", direction)
s2.metric("Entry (underlying)", f"{entry:,.2f}" if np.isfinite(entry) else "—")
s3.metric("Stop-loss (underlying)", f"{sl:,.2f}" if np.isfinite(sl) else "—")
s4.metric(f"Target (underlying, {rr:g}R)", f"{target:,.2f}" if np.isfinite(target) else "—")
st.write(f"**Planned risk budget:** ₹{risk_rupees:,.0f} ({risk_pct:.1f}% of ₹{capital:,.0f}). This is a budget, not a guarantee or option lot-size recommendation.")

st.subheader("Recent candles & indicators")
show_cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume", "EMA9", "EMA21", "RSI", "VWAP"] if c in df.columns]
st.dataframe(df[show_cols].tail(30), use_container_width=True, hide_index=True)
st.line_chart(df.set_index("Date")["Close"].tail(150) if "Date" in df.columns else df["Close"].tail(150))

st.subheader("Simple historical underlying backtest")
st.caption("Educational diagnostic only. Signals are generated on candle close and held for the next candle; excludes options premium, brokerage, slippage, taxes, and execution constraints. Not a profitability proof.")
bt = df.copy()
bt["long_signal"] = (bt["Close"] > bt["EMA9"]) & (bt["EMA9"] > bt["EMA21"]) & bt["RSI"].between(52, 68)
bt["short_signal"] = (bt["Close"] < bt["EMA9"]) & (bt["EMA9"] < bt["EMA21"]) & bt["RSI"].between(32, 48)
if bt["VWAP"].notna().any():
    bt["long_signal"] &= bt["Close"] >= bt["VWAP"]
    bt["short_signal"] &= bt["Close"] <= bt["VWAP"]
bt["position"] = np.select([bt["long_signal"], bt["short_signal"]], [1, -1], default=0)
bt["next_return"] = bt["Close"].shift(-1) / bt["Close"] - 1
bt["strategy_return"] = bt["position"] * bt["next_return"]
trades = bt[bt["position"] != 0].copy()
if trades.empty:
    st.info("Is selected sample mein signals/trades nahi mile. Iska matlab strategy achhi ya buri prove nahi hoti; data length/conditions inspect karo.")
else:
    total_return = (1 + trades["strategy_return"].fillna(0)).prod() - 1
    wins = int((trades["strategy_return"] > 0).sum())
    n = len(trades)
    c1, c2, c3 = st.columns(3)
    c1.metric("Signal candles", f"{n}")
    c2.metric("Win rate (next candle)", f"{wins/n*100:.1f}%")
    c3.metric("Compounded return (rough)", f"{total_return*100:.2f}%")
    st.dataframe(trades[[c for c in ["Date", "Close", "position", "next_return", "strategy_return"] if c in trades.columns]].tail(50), use_container_width=True, hide_index=True)

st.download_button("Download analysed candles CSV", df.to_csv(index=False).encode("utf-8"), "nifty_sentinel_analysis.csv", "text/csv")
st.markdown("---")
st.caption("No broker orders are placed. This is not financial advice. Public data may fail or be delayed. Validate any setup independently.")

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="centered")
st.title("📈 NIFTY SENTINEL")
st.caption("Simple NIFTY research signals • Manual trading only • ₹0 software target")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(period, interval):
    import yfinance as yf
    errors = []
    for ticker_symbol in ["^NSEI"]:
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(period=period, interval=interval, auto_adjust=False)
            if df is not None and not df.empty:
                df = df.reset_index()
                if "Datetime" in df.columns:
                    df = df.rename(columns={"Datetime": "Date"})
                return df, None
            errors.append("Public data source returned no candles.")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    return pd.DataFrame(), "; ".join(errors) or "No data"

def prepare(df):
    df = df.copy()
    rename = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in ("datetime", "timestamp", "time", "date"):
            rename[c] = "Date"
        elif lc in ("open", "high", "low", "close", "volume"):
            rename[c] = lc.title()
    df = df.rename(columns=rename)
    needed = ["Open", "High", "Low", "Close"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Date" in df:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
    df = df.dropna(subset=needed).drop_duplicates(subset=["Date"] if "Date" in df else None).reset_index(drop=True)
    if len(df) < 60:
        raise ValueError(f"Only {len(df)} valid candles. Need at least 60; select more history or upload CSV.")
    close, high, low = df["Close"], df["High"], df["Low"]
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = (100 - 100/(1+rs)).fillna(50)
    prev_close = close.shift(1)
    tr = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/14, adjust=False).mean()
    # Prior-period breakout levels exclude current candle to avoid look-ahead.
    df["PriorHigh20"] = high.shift(1).rolling(20).max()
    df["PriorLow20"] = low.shift(1).rolling(20).min()
    return df

def run_backtest(df, stop_atr=1.0, target_r=2.0, cost_points=2.0):
    # Signals confirmed at candle close; entry is next candle open.
    # Conservative intrabar rule: if both SL and target are touched in same bar, assume SL first.
    trades = []
    warm = max(50, 20)
    for i in range(warm, len(df)-1):
        row = df.iloc[i]
        nxt = df.iloc[i+1]
        if not np.isfinite(row["ATR"]) or row["ATR"] <= 0:
            continue
        long_sig = (row["Close"] > row["EMA20"] > row["EMA50"] and
                    row["Close"] > row["PriorHigh20"] and 52 <= row["RSI"] <= 72)
        short_sig = (row["Close"] < row["EMA20"] < row["EMA50"] and
                     row["Close"] < row["PriorLow20"] and 28 <= row["RSI"] <= 48)
        if not (long_sig or short_sig):
            continue
        side = 1 if long_sig else -1
        entry = float(nxt["Open"])
        risk = float(row["ATR"] * stop_atr)
        if risk <= 0 or not np.isfinite(entry):
            continue
        sl = entry - side*risk
        target = entry + side*risk*target_r
        exit_price = float(df.iloc[-1]["Close"])
        exit_i = len(df)-1
        reason = "End of sample"
        # Manage position from entry candle onward.
        for j in range(i+1, len(df)):
            bar = df.iloc[j]
            if side == 1:
                stop_hit = float(bar["Low"]) <= sl
                target_hit = float(bar["High"]) >= target
            else:
                stop_hit = float(bar["High"]) >= sl
                target_hit = float(bar["Low"]) <= target
            if stop_hit and target_hit:
                exit_price, exit_i, reason = sl, j, "SL (conservative same-bar rule)"
                break
            if stop_hit:
                exit_price, exit_i, reason = sl, j, "Stop-loss"
                break
            if target_hit:
                exit_price, exit_i, reason = target, j, "Target"
                break
        points = side*(exit_price-entry) - cost_points
        trades.append({
            "Signal date": row["Date"] if "Date" in df else i,
            "Entry date": nxt["Date"] if "Date" in df else i+1,
            "Side": "LONG underlying" if side == 1 else "SHORT underlying",
            "Entry": entry, "Stop": sl, "Target": target,
            "Exit": exit_price, "Exit reason": reason,
            "Net points after assumed costs": points,
            "R multiple after costs": points/risk,
            "Bars held": exit_i-(i+1)+1
        })
    return pd.DataFrame(trades)

with st.sidebar:
    st.header("Data")
    interval = st.selectbox("Candle size", ["15m", "30m", "1d"], index=0)
    period_options = {"15m": ["5d", "1mo"], "30m": ["5d", "1mo"], "1d": ["3mo", "6mo", "1y", "2y"]}
    period = st.selectbox("History", period_options[interval], index=len(period_options[interval])-1)
    st.header("Backtest assumptions")
    stop_atr = st.selectbox("Stop distance (ATR)", [0.75, 1.0, 1.25, 1.5], index=1)
    target_r = st.selectbox("Target (R)", [1.0, 1.5, 2.0, 2.5, 3.0], index=2)
    cost_points = st.number_input("Assumed round-trip cost (NIFTY points)", min_value=0.0, value=2.0, step=0.5)
    st.caption("Cost is a rough underlying-points proxy, not actual options brokerage/tax/slippage.")
uploaded = st.file_uploader("Optional: upload candle CSV", type=["csv"], help="Required columns: Date, Open, High, Low, Close; Volume optional.")
if st.button("Refresh data", type="primary"):
    st.cache_data.clear()

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        source = "Uploaded CSV"
    else:
        with st.spinner("Fetching public NIFTY candles..."):
            raw, err = fetch_data(period, interval)
        if raw.empty:
            st.error(f"Public market data is unavailable right now. Details: {err}")
            st.info("Try Daily candles with 1y history, or upload a candle CSV. No signal is shown without data.")
            st.stop()
        source = f"Public Yahoo Finance feed • {period} / {interval}"
    df = prepare(raw)
except Exception as exc:
    st.error(f"Could not process data: {type(exc).__name__}: {exc}")
    st.info("CSV columns must include Date (optional), Open, High, Low, Close; Volume is optional.")
    st.stop()

last = df.iloc[-1]
prev = df.iloc[-2]
close = float(last["Close"])
long_setup = close > last["EMA20"] > last["EMA50"] and close > last["PriorHigh20"] and 52 <= last["RSI"] <= 72
short_setup = close < last["EMA20"] < last["EMA50"] and close < last["PriorLow20"] and 28 <= last["RSI"] <= 48
if long_setup:
    signal, direction = "BULLISH BREAKOUT", "CE candidate (underlying bias only)"
    entry = close; sl = entry-float(last["ATR"])*stop_atr; target = entry+float(last["ATR"])*stop_atr*target_r
elif short_setup:
    signal, direction = "BEARISH BREAKDOWN", "PE candidate (underlying bias only)"
    entry = close; sl = entry+float(last["ATR"])*stop_atr; target = entry-float(last["ATR"])*stop_atr*target_r
else:
    signal, direction, entry, sl, target = "NO TRADE", "NONE", np.nan, np.nan, np.nan

st.caption(f"Data source: {source} • Latest candle: {last['Date'] if 'Date' in df else 'date unavailable'}")
if "Date" in df and pd.notna(last["Date"]):
    try:
        if pd.Timestamp(last["Date"]).tz_localize(None) < pd.Timestamp.now().normalize()-pd.Timedelta(days=3):
            st.warning("Latest candle may be stale. Check its timestamp before interpreting the signal.")
    except Exception:
        pass

a,b,c = st.columns(3)
a.metric("NIFTY close", f"{close:,.2f}", f"{close-float(prev['Close']):+.2f}")
b.metric("Signal", signal)
c.metric("RSI", f"{float(last['RSI']):.1f}")
st.subheader("Your signal")
if signal == "NO TRADE":
    st.info("NO TRADE — setup conditions are not all satisfied. Wait; do not force an entry.")
else:
    st.success(f"{direction}. Research signal only; confirm live data and option liquidity separately.")
    a,b,c = st.columns(3)
    a.metric("Underlying entry", f"{entry:,.2f}")
    b.metric("Underlying stop", f"{sl:,.2f}")
    c.metric("Underlying target", f"{target:,.2f}")
st.caption("These levels refer to NIFTY underlying, not the option premium. This app does not check live option chain, Greeks, spreads, or place orders.")

with st.expander("Show indicators and recent candles"):
    cols = [c for c in ["Date","Open","High","Low","Close","Volume","EMA20","EMA50","RSI","ATR","PriorHigh20","PriorLow20"] if c in df]
    st.dataframe(df[cols].tail(30), use_container_width=True, hide_index=True)
    if "Date" in df:
        st.line_chart(df.set_index("Date")["Close"].tail(200))
    else:
        st.line_chart(df["Close"].tail(200))

st.subheader("Historical strategy test")
st.caption("This tests NIFTY underlying price movement, not CE/PE option P&L. Assumes next-candle-open entries, ATR stops/targets, conservative SL-first handling if both are touched, and an editable approximate cost in index points. Still excludes real option pricing, taxes and market impact.")
trades = run_backtest(df, stop_atr=stop_atr, target_r=target_r, cost_points=cost_points)
if trades.empty:
    st.warning("No qualifying trades in this sample. Do not interpret this as proof of profitability or failure.")
else:
    wins = int((trades["Net points after assumed costs"] > 0).sum())
    gross_points = float(trades["Net points after assumed costs"].sum())
    win_rate = wins/len(trades)*100
    avg_r = float(trades["R multiple after costs"].mean())
    equity = trades["Net points after assumed costs"].cumsum()
    drawdown = equity-equity.cummax()
    max_dd = float(drawdown.min())
    a,b,c,d = st.columns(4)
    a.metric("Closed trades", str(len(trades)))
    b.metric("Win rate", f"{win_rate:.1f}%")
    c.metric("Net index points*", f"{gross_points:.1f}")
    d.metric("Average R*", f"{avg_r:.2f}")
    st.write(f"**Max trade-sequence drawdown:** {max_dd:.1f} index points (rough diagnostic).")
    st.dataframe(trades.tail(100), use_container_width=True, hide_index=True)
    st.download_button("Download backtest trades CSV", trades.to_csv(index=False).encode("utf-8"), "nifty_sentinel_backtest.csv", "text/csv")

st.download_button("Download analysed candles CSV", df.to_csv(index=False).encode("utf-8"), "nifty_sentinel_candles.csv", "text/csv")
st.divider()
st.caption("No automated orders. No guaranteed returns. Never expose API keys in a public repository. Validate independently before risking money.")

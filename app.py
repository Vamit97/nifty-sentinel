import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="centered")
st.title("📈 NIFTY SENTINEL")
st.caption("Simple research dashboard • Free public data • No broker orders")

st.warning("Research only: this tests NIFTY index candles, NOT actual CE/PE option premiums. No signal guarantees profit.")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(period, interval):
    import yfinance as yf
    try:
        raw = yf.Ticker("^NSEI").history(period=period, interval=interval, auto_adjust=False)
        if raw is None or raw.empty:
            return pd.DataFrame(), "The public feed returned no candles."
        raw = raw.reset_index()
        if "Datetime" in raw.columns:
            raw = raw.rename(columns={"Datetime": "Date"})
        return raw, None
    except Exception as exc:
        return pd.DataFrame(), f"{type(exc).__name__}: {exc}"

def prepare(raw):
    df = raw.copy()
    rename = {}
    for col in df.columns:
        name = str(col).strip().lower()
        if name in ("date", "datetime", "timestamp", "time"):
            rename[col] = "Date"
        elif name in ("open", "high", "low", "close", "volume"):
            rename[col] = name.title()
    df = df.rename(columns=rename)
    required = ["Open", "High", "Low", "Close"]
    missing = [x for x in required if x not in df.columns]
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(missing))
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Date" in df:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
        df = df.drop_duplicates(subset=["Date"], keep="last")
    df = df.dropna(subset=required).reset_index(drop=True)
    if len(df) < 100:
        raise ValueError(f"Only {len(df)} valid candles. At least 100 are required; choose more history or upload a larger CSV.")
    close, high, low = df["Close"], df["High"], df["Low"]
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()
    change = close.diff()
    avg_gain = change.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = (-change.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = (100 - 100/(1+rs)).fillna(50)
    prev_close = close.shift(1)
    tr = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/14, adjust=False).mean()
    # Shift prior-period levels so the current candle is excluded.
    df["PriorHigh20"] = high.shift(1).rolling(20).max()
    df["PriorLow20"] = low.shift(1).rolling(20).min()
    return df

def signal_for(row):
    fields = ["Close", "EMA20", "EMA50", "RSI", "PriorHigh20", "PriorLow20"]
    if any(pd.isna(row[x]) for x in fields):
        return 0
    if row["Close"] > row["EMA20"] > row["EMA50"] and row["Close"] > row["PriorHigh20"] and 52 <= row["RSI"] <= 72:
        return 1
    if row["Close"] < row["EMA20"] < row["EMA50"] and row["Close"] < row["PriorLow20"] and 28 <= row["RSI"] <= 48:
        return -1
    return 0

def backtest(df, start_i, end_i, stop_atr, target_r, cost_points):
    """
    Non-overlapping trades. Signal at candle i close; entry at candle i+1 open.
    Trades must exit within the assigned window. Any position still open at window end
    is marked to market and labeled separately; it is not counted as a completed SL/target trade.
    Same-bar SL and target => assume SL first.
    """
    rows = []
    start_i = max(51, int(start_i))
    end_i = min(int(end_i), len(df)-1)
    i = start_i
    while i < end_i:
        sig = signal_for(df.iloc[i])
        atr = df.iloc[i]["ATR"]
        if sig == 0 or pd.isna(atr) or atr <= 0:
            i += 1
            continue
        entry_i = i + 1
        if entry_i > end_i:
            break
        entry = float(df.iloc[entry_i]["Open"])
        risk = float(atr * stop_atr)
        if not np.isfinite(entry) or risk <= 0:
            i += 1
            continue
        stop = entry - sig*risk
        target = entry + sig*risk*target_r
        exit_price = float(df.iloc[end_i]["Close"])
        exit_i = end_i
        reason = "Window-end mark-to-market (not closed by SL/target)"
        completed = False
        for j in range(entry_i, end_i+1):
            bar = df.iloc[j]
            if sig == 1:
                stop_hit = float(bar["Low"]) <= stop
                target_hit = float(bar["High"]) >= target
            else:
                stop_hit = float(bar["High"]) >= stop
                target_hit = float(bar["Low"]) <= target
            if stop_hit and target_hit:
                exit_price, exit_i, reason, completed = stop, j, "Stop-loss (same-bar conservative rule)", True
                break
            if stop_hit:
                exit_price, exit_i, reason, completed = stop, j, "Stop-loss", True
                break
            if target_hit:
                exit_price, exit_i, reason, completed = target, j, "Target", True
                break
        net_points = sig*(exit_price-entry) - cost_points
        rows.append({
            "Signal date": df.iloc[i]["Date"] if "Date" in df else i,
            "Entry date": df.iloc[entry_i]["Date"] if "Date" in df else entry_i,
            "Side": "LONG underlying" if sig == 1 else "SHORT underlying",
            "Entry": entry, "Stop": stop, "Target": target, "Exit": exit_price,
            "Exit reason": reason, "Completed by SL/target": completed,
            "Net points after assumed costs": net_points,
            "R multiple after assumed costs": net_points/risk,
            "Bars held": exit_i-entry_i+1
        })
        # Do not open another position until this one has ended.
        i = exit_i + 1
    return pd.DataFrame(rows)

def stats(trades):
    if trades.empty:
        return None
    p = trades["Net points after assumed costs"].astype(float)
    wins = p > 0
    gp = float(p[p > 0].sum())
    gl = float(-p[p < 0].sum())
    # Trade-sequence equity and drawdown, using realized/marked trade outcomes.
    equity = p.cumsum()
    peak = equity.cummax().clip(lower=0)
    max_dd = float((equity-peak).min())
    return {
        "n": len(trades),
        "completed": int(trades["Completed by SL/target"].sum()),
        "win": float(wins.mean()*100),
        "net": float(p.sum()),
        "pf": gp/gl if gl > 0 else (float("inf") if gp > 0 else 0.0),
        "avg_r": float(trades["R multiple after costs"].mean()),
        "dd": max_dd,
    }

with st.sidebar:
    st.header("Data settings")
    interval = st.selectbox("Candle interval", ["15m", "30m", "1d"], index=0)
    choices = {"15m":["5d","1mo"], "30m":["5d","1mo"], "1d":["6mo","1y","2y","5y"]}
    period = st.selectbox("History", choices[interval], index=len(choices[interval])-1)
    st.header("Test assumptions")
    stop_atr = st.selectbox("Stop distance (ATR)", [0.75, 1.0, 1.25, 1.5], index=1)
    target_r = st.selectbox("Target (R)", [1.0, 1.5, 2.0, 2.5, 3.0], index=2)
    cost_points = st.number_input("Assumed cost per trade (index points)", min_value=0.0, value=2.0, step=0.5)
    st.caption("This is a rough underlying-point deduction, not actual options brokerage/taxes.")

upload = st.file_uploader("Optional: upload candle CSV", type=["csv"], help="Required columns: Open, High, Low, Close. Date optional; Volume optional.")
if st.button("Refresh market data", type="primary"):
    st.cache_data.clear()

try:
    if upload is not None:
        raw = pd.read_csv(upload)
        source = "Uploaded CSV"
    else:
        with st.spinner("Fetching public NIFTY candles..."):
            raw, error = fetch_data(period, interval)
        if raw.empty:
            st.error(f"Market data unavailable: {error}")
            st.info("Try Daily + 1y history, or upload candle CSV. No signal is produced without data.")
            st.stop()
        source = f"Public feed • {period} / {interval}"
    df = prepare(raw)
except Exception as exc:
    st.error(f"Data error: {type(exc).__name__}: {exc}")
    st.info("CSV needs at least 100 valid candles and columns Open, High, Low, Close.")
    st.stop()

last, prev = df.iloc[-1], df.iloc[-2]
if "Date" in df and pd.notna(last["Date"]):
    try:
        stamp = pd.Timestamp(last["Date"])
        now = pd.Timestamp.now(tz=stamp.tz) if stamp.tzinfo else pd.Timestamp.now()
        if now - stamp > pd.Timedelta(days=3):
            st.warning("Latest candle looks older than 3 days. Verify the timestamp; do not treat it as a live signal.")
    except Exception:
        pass

sig = signal_for(last)
label = "BULLISH BREAKOUT" if sig == 1 else ("BEARISH BREAKDOWN" if sig == -1 else "NO TRADE")
a,b,c = st.columns(3)
a.metric("NIFTY close", f"{float(last['Close']):,.2f}", f"{float(last['Close']-prev['Close']):+.2f}")
b.metric("Signal", label)
c.metric("RSI", f"{float(last['RSI']):.1f}")
st.caption(f"Source: {source} • Latest candle: {last['Date'] if 'Date' in df else 'date unavailable'}")

if sig:
    entry = float(last["Close"])
    risk = float(last["ATR"])*stop_atr
    stop = entry-sig*risk
    target = entry+sig*risk*target_r
    a,b,c = st.columns(3)
    a.metric("Underlying reference", f"{entry:,.2f}")
    b.metric("Underlying stop", f"{stop:,.2f}")
    c.metric("Underlying target", f"{target:,.2f}")
else:
    st.info("NO TRADE — wait for all conditions; do not force an entry.")
st.caption("These are NIFTY underlying levels, not CE/PE premium levels. No live option chain, Greeks, IV, spreads or broker execution.")

with st.expander("Indicators and recent candles"):
    cols = [x for x in ["Date","Open","High","Low","Close","Volume","EMA20","EMA50","RSI","ATR","PriorHigh20","PriorLow20"] if x in df]
    st.dataframe(df[cols].tail(30), use_container_width=True, hide_index=True)
    if "Date" in df:
        st.line_chart(df.set_index("Date")["Close"].tail(200))
    else:
        st.line_chart(df["Close"].tail(200))

st.subheader("Historical test")
st.caption("Chronological 70/30 split. Signals use candle close; entry uses next candle open. Only one position at a time. Trades are confined to each window; unfinished trades are marked at window end and clearly labeled. Same-candle SL and target assumes SL first.")
split = int(len(df)*0.70)
for title, start, end, key in [
    ("Development window (first 70%)", 51, split-1, "dev"),
    ("Out-of-sample window (last 30%)", max(51,split-1), len(df)-1, "oos")
]:
    trades = backtest(df, start, end, stop_atr, target_r, cost_points) if end > start else pd.DataFrame()
    st.markdown(f"**{title}**")
    s = stats(trades)
    if s is None:
        st.info("No qualifying trades in this window.")
        continue
    a,b,c,d = st.columns(4)
    a.metric("Trades", str(s["n"]), help=f"{s['completed']} exited by SL/target; remainder marked at window end.")
    b.metric("Win rate", f"{s['win']:.1f}%")
    c.metric("Net points*", f"{s['net']:.1f}")
    d.metric("Profit factor*", f"{s['pf']:.2f}" if np.isfinite(s["pf"]) else "∞")
    st.write(f"Average R*: **{s['avg_r']:.2f}** · Max trade-sequence drawdown*: **{s['dd']:.1f} points** · SL/target exits: **{s['completed']}**")
    if key == "oos":
        if s["n"] < 20:
            st.warning("Too few out-of-sample trades (<20) for a reliable conclusion. Keep paper-testing; do not use this as a live-options proof.")
        elif s["net"] <= 0 or s["pf"] <= 1:
            st.warning("Out-of-sample performance is not positive under these assumptions. Do not use live.")
        else:
            st.info("Positive in this sample only; continue paper testing. This is not proof of future profitability.")
    st.dataframe(trades, use_container_width=True, hide_index=True)
    st.download_button(f"Download {key.upper()} trades CSV", trades.to_csv(index=False).encode("utf-8"), f"nifty_sentinel_{key}_trades.csv", "text/csv", key=f"dl_{key}")

st.download_button("Download analysed candles CSV", df.to_csv(index=False).encode("utf-8"), "nifty_sentinel_candles.csv", "text/csv")
st.caption("No orders are placed. Backtest is for NIFTY underlying only; actual option P&L requires historical option premiums and realistic costs. Never upload API keys to a public repo.")

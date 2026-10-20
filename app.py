import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="centered")
st.title("📈 NIFTY SENTINEL")
st.caption("Simple research dashboard • Manual signals only • No broker orders")

st.warning("This app uses NIFTY underlying candles, not CE/PE option premiums or live option-chain confirmation. It cannot guarantee profits.")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(period, interval):
    import yfinance as yf
    try:
        df = yf.Ticker("^NSEI").history(period=period, interval=interval, auto_adjust=False)
        if df is None or df.empty:
            return pd.DataFrame(), "Public feed returned no candles."
        df = df.reset_index()
        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"{type(e).__name__}: {e}"

def prepare(raw):
    df = raw.copy()
    rename = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ("date", "datetime", "timestamp", "time"): rename[col] = "Date"
        elif c in ("open", "high", "low", "close", "volume"): rename[col] = c.title()
    df = df.rename(columns=rename)
    req = ["Open", "High", "Low", "Close"]
    missing = [c for c in req if c not in df]
    if missing: raise ValueError("Missing columns: " + ", ".join(missing))
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Date" in df:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
    df = df.dropna(subset=req).reset_index(drop=True)
    if len(df) < 100:
        raise ValueError(f"Only {len(df)} candles found. Need at least 100 for this diagnostic.")
    c, h, l = df.Close, df.High, df.Low
    df["EMA20"] = c.ewm(span=20, adjust=False).mean()
    df["EMA50"] = c.ewm(span=50, adjust=False).mean()
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    df["RSI"] = (100 - 100/(1+rs)).fillna(50)
    prev = c.shift()
    tr = pd.concat([h-l, (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/14, adjust=False).mean()
    df["PriorHigh20"] = h.shift(1).rolling(20).max()
    df["PriorLow20"] = l.shift(1).rolling(20).min()
    return df

def signal_for(row):
    vals = [row.get("Close"), row.get("EMA20"), row.get("EMA50"), row.get("RSI"), row.get("PriorHigh20"), row.get("PriorLow20")]
    if any(pd.isna(x) for x in vals): return 0
    if row["Close"] > row["EMA20"] > row["EMA50"] and row["Close"] > row["PriorHigh20"] and 52 <= row["RSI"] <= 72:
        return 1
    if row["Close"] < row["EMA20"] < row["EMA50"] and row["Close"] < row["PriorLow20"] and 28 <= row["RSI"] <= 48:
        return -1
    return 0

def backtest_single_position(df, start_i, end_i, stop_atr=1.0, target_r=2.0, cost_points=2.0):
    # One position at a time. Signal on close, entry next candle open.
    # If SL and target are both touched in one candle, pessimistically assume SL first.
    trades = []
    i = max(start_i, 51)
    while i < min(end_i, len(df)-1):
        sig = signal_for(df.iloc[i])
        atr = df.iloc[i]["ATR"]
        if sig == 0 or pd.isna(atr) or atr <= 0:
            i += 1
            continue
        entry_i = i+1
        entry = float(df.iloc[entry_i]["Open"])
        risk = float(atr * stop_atr)
        if not np.isfinite(entry) or risk <= 0:
            i += 1
            continue
        sl = entry - sig*risk
        tgt = entry + sig*risk*target_r
        exit_price, exit_i, reason = float(df.iloc[min(end_i, len(df)-1)]["Close"]), min(end_i, len(df)-1), "End of test window"
        for j in range(entry_i, min(end_i, len(df)-1)+1):
            bar = df.iloc[j]
            if sig == 1:
                stop_hit = float(bar["Low"]) <= sl
                target_hit = float(bar["High"]) >= tgt
            else:
                stop_hit = float(bar["High"]) >= sl
                target_hit = float(bar["Low"]) <= tgt
            if stop_hit and target_hit:
                exit_price, exit_i, reason = sl, j, "Stop-loss (same-candle conservative rule)"
                break
            elif stop_hit:
                exit_price, exit_i, reason = sl, j, "Stop-loss"
                break
            elif target_hit:
                exit_price, exit_i, reason = tgt, j, "Target"
                break
        net_pts = sig*(exit_price-entry) - cost_points
        trades.append({
            "Signal date": df.iloc[i]["Date"] if "Date" in df else i,
            "Entry date": df.iloc[entry_i]["Date"] if "Date" in df else entry_i,
            "Side": "LONG underlying" if sig == 1 else "SHORT underlying",
            "Entry": entry, "Stop": sl, "Target": tgt, "Exit": exit_price,
            "Exit reason": reason, "Net points after assumed costs": net_pts,
            "R multiple after costs": net_pts/risk, "Bars held": exit_i-entry_i+1
        })
        # Avoid overlapping positions/repeated signals while a position is open.
        i = exit_i + 1
    return pd.DataFrame(trades)

def summarize(trades):
    if trades.empty:
        return None
    pnl = trades["Net points after assumed costs"].astype(float)
    wins = pnl > 0
    equity = pnl.cumsum()
    dd = equity - equity.cummax()
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = -pnl[pnl < 0].sum()
    return {
        "trades": len(trades),
        "win_rate": 100*float(wins.mean()),
        "net_points": float(pnl.sum()),
        "avg_r": float(trades["R multiple after costs"].mean()),
        "max_dd": float(dd.min()),
        "profit_factor": float(gross_profit/gross_loss) if gross_loss > 0 else np.inf,
    }

with st.sidebar:
    st.header("Data")
    interval = st.selectbox("Candle size", ["15m", "30m", "1d"], index=0)
    periods = {"15m":["5d","1mo"], "30m":["5d","1mo"], "1d":["6mo","1y","2y","5y"]}
    period = st.selectbox("History", periods[interval], index=len(periods[interval])-1)
    st.header("Backtest assumptions")
    stop_atr = st.selectbox("Stop distance (ATR)", [0.75,1.0,1.25,1.5], index=1)
    target_r = st.selectbox("Target (R)", [1.0,1.5,2.0,2.5,3.0], index=2)
    cost_points = st.number_input("Assumed round-trip cost (index points)", min_value=0.0, value=2.0, step=0.5)
    st.caption("Cost is an illustrative index-point deduction, not actual options costs.")

uploaded = st.file_uploader("Optional: upload candle CSV", type=["csv"], help="Columns: Date, Open, High, Low, Close; Volume optional.")
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
            st.error(f"Public market data unavailable: {err}")
            st.info("Try Daily + 1y history, or upload a candle CSV. No signal is shown without data.")
            st.stop()
        source = f"Public feed • {period}/{interval}"
    df = prepare(raw)
except Exception as e:
    st.error(f"Could not process data: {type(e).__name__}: {e}")
    st.info("Upload a CSV with Date, Open, High, Low, Close columns and at least 100 valid candles.")
    st.stop()

last, prev = df.iloc[-1], df.iloc[-2]
sig = signal_for(last)
if sig == 1:
    label, direction = "BULLISH BREAKOUT", "CE candidate — underlying bias only"
elif sig == -1:
    label, direction = "BEARISH BREAKDOWN", "PE candidate — underlying bias only"
else:
    label, direction = "NO TRADE", "NONE"

st.caption(f"Source: {source} • Latest candle: {last['Date'] if 'Date' in df else 'date unavailable'}")
a,b,c = st.columns(3)
a.metric("NIFTY close", f"{float(last['Close']):,.2f}", f"{float(last['Close']-prev['Close']):+.2f}")
b.metric("Signal", label)
c.metric("RSI", f"{float(last['RSI']):.1f}")
if sig:
    atr = float(last["ATR"])
    entry = float(last["Close"])
    sl = entry - sig*atr*stop_atr
    tgt = entry + sig*atr*stop_atr*target_r
    a,b,c = st.columns(3)
    a.metric("Underlying entry reference", f"{entry:,.2f}")
    b.metric("Underlying stop", f"{sl:,.2f}")
    c.metric("Underlying target", f"{tgt:,.2f}")
else:
    st.info("NO TRADE — wait for all conditions. Do not force a setup.")
st.caption("Underlying levels only, not option premiums. No live option-chain, IV, Greeks, spreads, or broker execution.")

with st.expander("Indicators and recent candles"):
    columns = [c for c in ["Date","Open","High","Low","Close","Volume","EMA20","EMA50","RSI","ATR","PriorHigh20","PriorLow20"] if c in df]
    st.dataframe(df[columns].tail(30), use_container_width=True, hide_index=True)
    if "Date" in df:
        st.line_chart(df.set_index("Date")["Close"].tail(200))
    else:
        st.line_chart(df["Close"].tail(200))

st.subheader("Backtest with one position at a time")
st.caption("Chronological split: first 70% of candles is the development window; final 30% is held out for a simple out-of-sample check. Signals are confirmed at candle close, entered at next candle open, and held until stop/target/end. If SL and target touch in one candle, SL is assumed first. This remains a rough underlying-only test.")
split = int(len(df)*0.70)
train = backtest_single_position(df, 51, max(52, split-1), stop_atr, target_r, cost_points)
test = backtest_single_position(df, max(51, split-1), len(df)-1, stop_atr, target_r, cost_points)
for title, trades in [("Development window (first 70%)", train), ("Out-of-sample window (last 30%)", test)]:
    st.markdown(f"**{title}**")
    s = summarize(trades)
    if s is None:
        st.info("No qualifying trades in this window.")
        continue
    a,b,c,d = st.columns(4)
    a.metric("Closed trades", str(s["trades"]))
    b.metric("Win rate", f"{s['win_rate']:.1f}%")
    c.metric("Net index points*", f"{s['net_points']:.1f}")
    d.metric("Profit factor*", f"{s['profit_factor']:.2f}" if np.isfinite(s["profit_factor"]) else "∞")
    st.write(f"Average R*: **{s['avg_r']:.2f}** · Max trade-sequence drawdown*: **{s['max_dd']:.1f} points**")
    if title.startswith("Out-of-sample"):
        if s["trades"] < 10:
            st.warning("Too few out-of-sample trades to draw a reliable conclusion.")
        elif s["net_points"] <= 0 or s["profit_factor"] <= 1:
            st.warning("Out-of-sample test is not positive under these assumptions. Do not use live.")
        else:
            st.info("Out-of-sample result is positive in this sample only; it is not proof of future profitability.")
    st.dataframe(trades, use_container_width=True, hide_index=True)
    st.download_button(f"Download {title.split('(')[0].strip()} trades CSV", trades.to_csv(index=False).encode("utf-8"), f"nifty_sentinel_{'oos' if title.startswith('Out') else 'development'}_trades.csv", "text/csv", key=title)

st.download_button("Download analysed candles CSV", df.to_csv(index=False).encode("utf-8"), "nifty_sentinel_candles.csv", "text/csv")
st.divider()
st.caption("Research prototype only. No option-premium profitability is measured and no orders are placed. Never expose API keys in a public repository.")

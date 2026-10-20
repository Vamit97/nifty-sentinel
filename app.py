import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NIFTY SENTINEL", page_icon="📈", layout="centered")
st.title("📈 NIFTY SENTINEL v7")
st.caption("Strategy comparison • Historical research • No broker orders")
st.warning("Research only. NIFTY underlying points are not CE/PE option P&L. This app cannot guarantee profits.")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(period, interval):
    import yfinance as yf
    try:
        raw = yf.Ticker("^NSEI").history(period=period, interval=interval, auto_adjust=False)
        if raw is None or raw.empty:
            return pd.DataFrame(), "Public feed returned no candles."
        raw = raw.reset_index()
        if "Datetime" in raw.columns:
            raw = raw.rename(columns={"Datetime": "Date"})
        return raw, None
    except Exception as exc:
        return pd.DataFrame(), f"{type(exc).__name__}: {exc}"

def normalize(raw):
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
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Date" in df:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date").drop_duplicates("Date", keep="last")
    df = df.dropna(subset=required).reset_index(drop=True)
    if len(df) < 100:
        raise ValueError(f"Only {len(df)} valid candles. At least 100 are needed.")
    return df

def indicators(raw):
    df = normalize(raw)
    c, h, l = df["Close"], df["High"], df["Low"]
    df["EMA20"] = c.ewm(span=20, adjust=False, min_periods=20).mean()
    df["EMA50"] = c.ewm(span=50, adjust=False, min_periods=50).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((gain == 0) & (loss > 0), 0)
    df["RSI"] = rsi.fillna(50)
    prev = c.shift(1)
    tr = pd.concat([h-l, (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    df["PriorHigh20"] = h.shift(1).rolling(20, min_periods=20).max()
    df["PriorLow20"] = l.shift(1).rolling(20, min_periods=20).min()
    df["TrendStrength"] = (df["EMA20"] - df["EMA50"]).abs() / df["ATR"].replace(0, np.nan)
    df["ATRpct"] = 100 * df["ATR"] / df["Close"]
    return df

def signal(row, strategy):
    fields = ["Close", "EMA20", "EMA50", "RSI", "ATR"]
    if any(pd.isna(row[x]) for x in fields) or row["ATR"] <= 0:
        return 0
    if strategy == "Breakout":
        if pd.isna(row["PriorHigh20"]) or pd.isna(row["PriorLow20"]):
            return 0
        if row["Close"] > row["EMA20"] > row["EMA50"] and row["Close"] > row["PriorHigh20"] and 52 <= row["RSI"] <= 72:
            return 1
        if row["Close"] < row["EMA20"] < row["EMA50"] and row["Close"] < row["PriorLow20"] and 28 <= row["RSI"] <= 48:
            return -1
    elif strategy == "Trend Pullback":
        # Experimental trend-following filter, not assumed profitable.
        if row["EMA20"] > row["EMA50"] and row["Close"] > row["EMA50"] and 45 <= row["RSI"] <= 62 and row["Close"] >= row["EMA20"]:
            return 1
        if row["EMA20"] < row["EMA50"] and row["Close"] < row["EMA50"] and 38 <= row["RSI"] <= 55 and row["Close"] <= row["EMA20"]:
            return -1
    return 0

def backtest(df, start, end, strategy, stop_atr, target_r, cost_points, max_hold):
    trades = []
    start, end = max(60, int(start)), min(int(end), len(df)-1)
    i = start
    while i < end:
        side = signal(df.iloc[i], strategy)
        atr = df.iloc[i]["ATR"]
        if side == 0 or pd.isna(atr) or atr <= 0:
            i += 1
            continue
        entry_i = i + 1
        if entry_i > end:
            break
        entry = float(df.iloc[entry_i]["Open"])
        risk = float(atr * stop_atr)
        if not np.isfinite(entry) or risk <= 0:
            i += 1
            continue
        stop = entry - side*risk
        target = entry + side*risk*target_r
        last_i = min(end, entry_i + max_hold - 1)
        exit_price, exit_i = float(df.iloc[last_i]["Close"]), last_i
        reason, completed = "Window-end mark (unfinished)", False
        for j in range(entry_i, last_i+1):
            bar = df.iloc[j]
            stop_hit = float(bar["Low"]) <= stop if side == 1 else float(bar["High"]) >= stop
            target_hit = float(bar["High"]) >= target if side == 1 else float(bar["Low"]) <= target
            if stop_hit and target_hit:
                exit_price, exit_i, reason, completed = stop, j, "Stop-loss (conservative same-candle rule)", True
                break
            if stop_hit:
                exit_price, exit_i, reason, completed = stop, j, "Stop-loss", True
                break
            if target_hit:
                exit_price, exit_i, reason, completed = target, j, "Target", True
                break
        if not completed and last_i < end and (exit_i-entry_i+1) >= max_hold:
            reason, completed = "Time exit at candle close", True
        net = side*(exit_price-entry) - cost_points
        trades.append({
            "Strategy": strategy,
            "Signal date": df.iloc[i]["Date"] if "Date" in df else i,
            "Entry date": df.iloc[entry_i]["Date"] if "Date" in df else entry_i,
            "Side": "LONG underlying" if side == 1 else "SHORT underlying",
            "Entry": entry, "Stop": stop, "Target": target, "Exit": exit_price,
            "Exit reason": reason, "Completed trade": completed,
            "Net index points after assumed cost": net,
            "R multiple after assumed cost": net/risk,
            "Bars held": exit_i-entry_i+1
        })
        i = exit_i + 1  # one position at a time
    return pd.DataFrame(trades)

def metrics(trades):
    if trades.empty:
        return None
    completed = trades[trades["Completed trade"]].copy()
    p = completed["Net index points after assumed cost"].astype(float)
    gross_profit = float(p[p > 0].sum())
    gross_loss = float(-p[p < 0].sum())
    equity = p.cumsum().reset_index(drop=True)
    peaks = pd.concat([pd.Series([0.0]), equity], ignore_index=True).cummax().iloc[1:].reset_index(drop=True)
    dd = float((equity-peaks).min()) if len(equity) else 0.0
    return {
        "setups": len(trades), "completed": len(completed), "unfinished": len(trades)-len(completed),
        "win_rate": float((p > 0).mean()*100) if len(p) else np.nan,
        "net_completed": float(p.sum()) if len(p) else 0.0,
        "net_all": float(trades["Net index points after assumed cost"].sum()),
        "profit_factor": gross_profit/gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0),
        "avg_r": float(completed["R multiple after assumed cost"].mean()) if len(completed) else np.nan,
        "drawdown": dd
    }

with st.sidebar:
    st.header("Market data")
    interval = st.selectbox("Candle interval", ["15m", "30m", "1d"], index=0)
    periods = {"15m": ["5d", "1mo"], "30m": ["5d", "1mo"], "1d": ["6mo", "1y", "2y", "5y"]}
    period = st.selectbox("History", periods[interval], index=len(periods[interval])-1)
    st.caption("Free public intraday feeds are limited. Daily 5y gives more history but is a different timeframe.")
    st.header("Backtest assumptions")
    stop_atr = st.selectbox("Stop distance (ATR)", [0.75, 1.0, 1.25, 1.5], index=1)
    target_r = st.selectbox("Target (R)", [1.0, 1.5, 2.0, 2.5, 3.0], index=2)
    max_hold = st.selectbox("Maximum holding candles", [4, 8, 12, 20], index=1)
    cost_points = st.number_input("Assumed cost per trade (index points)", min_value=0.0, value=2.0, step=0.5)
    st.caption("Illustrative index-point deduction, not actual option brokerage/taxes.")

uploads = st.file_uploader("Upload one or more candle CSV files", type=["csv"], accept_multiple_files=True,
                            help="Required columns: Open, High, Low, Close. Date recommended. Multiple files are merged and duplicate timestamps removed.")
if st.button("Refresh market data", type="primary"):
    st.cache_data.clear()

try:
    if uploads:
        pieces = [pd.read_csv(f) for f in uploads]
        raw = pd.concat(pieces, ignore_index=True)
        source = f"{len(uploads)} uploaded CSV file(s)"
    else:
        with st.spinner("Fetching public NIFTY candles..."):
            raw, err = fetch_data(period, interval)
        if raw.empty:
            st.error(f"Market data unavailable: {err}")
            st.info("Try Daily + 5y for longer free history, or upload candle CSV files.")
            st.stop()
        source = f"Public feed • {period}/{interval}"
    df = indicators(raw)
except Exception as exc:
    st.error(f"Data error: {type(exc).__name__}: {exc}")
    st.info("CSV needs Date (recommended), Open, High, Low, Close, and at least 100 valid candles.")
    st.stop()

if "Date" in df and df["Date"].notna().any():
    first_date, last_date = df["Date"].iloc[0], df["Date"].iloc[-1]
    st.caption(f"Data: {source} • {len(df)} candles • {first_date} to {last_date}")
    try:
        stamp = pd.Timestamp(last_date)
        now = pd.Timestamp.now(tz=stamp.tz) if stamp.tzinfo else pd.Timestamp.now()
        if now-stamp > pd.Timedelta(days=3):
            st.warning("Latest candle may be stale. Verify the timestamp before using any signal.")
    except Exception:
        pass
else:
    st.caption(f"Data: {source} • {len(df)} candles")

last, prev = df.iloc[-1], df.iloc[-2]
current_signal = signal(last, "Breakout")
a,b,c = st.columns(3)
a.metric("NIFTY close", f"{float(last['Close']):,.2f}", f"{float(last['Close']-prev['Close']):+.2f}")
b.metric("Breakout signal", "BULLISH" if current_signal==1 else ("BEARISH" if current_signal==-1 else "NO TRADE"))
c.metric("RSI", f"{float(last['RSI']):.1f}")
if current_signal:
    ref=float(last["Close"]); risk=float(last["ATR"])*stop_atr
    a,b,c=st.columns(3)
    a.metric("Underlying reference",f"{ref:,.2f}")
    b.metric("Underlying stop",f"{ref-current_signal*risk:,.2f}")
    c.metric("Underlying target",f"{ref+current_signal*risk*target_r:,.2f}")
else:
    st.info("NO TRADE under the Breakout rules. Do not force a setup.")
st.caption("These are NIFTY underlying levels only, not CE/PE option-premium levels. No live option chain, IV, Greeks or broker execution.")

with st.expander("Recent candles and indicators"):
    cols=[c for c in ["Date","Open","High","Low","Close","Volume","EMA20","EMA50","RSI","ATR","PriorHigh20","PriorLow20","TrendStrength","ATRpct"] if c in df]
    st.dataframe(df[cols].tail(30), use_container_width=True, hide_index=True)
    if "Date" in df:
        st.line_chart(df.set_index("Date")["Close"].tail(300))
    else:
        st.line_chart(df["Close"].tail(300))

st.subheader("Same-data strategy comparison")
st.caption("Both strategies use identical chronological windows and assumptions. The current dataset has already been inspected, so its out-of-sample slice is no longer a truly untouched final validation set. Use newer/fresh data before considering real money.")
split=int(len(df)*0.70)
for title,start,end,key in [("Development window (first 70%)",60,split-1,"dev"),
                            ("Out-of-sample window (last 30%)",split,len(df)-1,"oos")]:
    st.markdown(f"**{title}**")
    rows=[]
    for strategy in ["Breakout","Trend Pullback"]:
        trades=backtest(df,start,end,strategy,stop_atr,target_r,cost_points,max_hold) if end>start else pd.DataFrame()
        m=metrics(trades)
        if m:
            rows.append({
                "Strategy":strategy,"Setups":m["setups"],"Completed":m["completed"],"Unfinished":m["unfinished"],
                "Win rate %":round(m["win_rate"],1) if np.isfinite(m["win_rate"]) else np.nan,
                "Completed net points":round(m["net_completed"],1),
                "Net incl. unfinished marks":round(m["net_all"],1),
                "Profit factor":round(m["profit_factor"],2) if np.isfinite(m["profit_factor"]) else np.inf,
                "Average R":round(m["avg_r"],2) if np.isfinite(m["avg_r"]) else np.nan,
                "Max completed DD":round(m["drawdown"],1)
            })
            with st.expander(f"{strategy}: trade log"):
                st.dataframe(trades,use_container_width=True,hide_index=True)
                st.download_button(f"Download {key} {strategy} trade log",trades.to_csv(index=False).encode("utf-8"),
                                   f"nifty_{key}_{strategy.lower().replace(' ','_')}_trades.csv","text/csv",
                                   key=f"{key}_{strategy}")
    if rows:
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        if key=="oos":
            enough=all(x["Completed"]>=20 for x in rows)
            if not enough:
                st.warning("At least one strategy has fewer than 20 completed out-of-sample trades. Evidence is insufficient; continue paper testing.")
            elif any((x["Completed net points"]<=0 or x["Profit factor"]<=1) for x in rows):
                st.warning("At least one strategy is not positive out-of-sample under these assumptions. Do not use live.")
            else:
                st.info("Results are positive in this sample only. Fresh-data validation is still needed.")

st.download_button("Download merged, analysed candles CSV",df.to_csv(index=False).encode("utf-8"),
                   "nifty_sentinel_merged_candles.csv","text/csv")
st.caption("Research prototype only. No orders are placed. Real CE/PE P&L requires historical option premiums, spreads, fees and realistic fills. Never upload API keys to a public repository.")

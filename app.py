from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import math
import hashlib
import re
import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

TZ = ZoneInfo('Asia/Kolkata')
BASE = 'https://api.groww.in/v1'
st.set_page_config(page_title='NIFTY SENTINEL', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
:root{--bg:#0b1118;--panel:#121d28;--line:#273847;--text:#edf4f8;--muted:#94a7b7;--green:#20d18a;--red:#ff6978;--gold:#efc56c}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:var(--text)}.stApp{background:radial-gradient(ellipse at 10% 0%,#172b3a 0%,var(--bg) 50%)}.block-container{max-width:1250px;padding:1rem 1rem 2rem}
[data-testid="stHeader"]{background:transparent}[data-testid="stSidebar"]{background:#0d1720;border-right:1px solid var(--line)}[data-testid="stSidebar"] *{color:var(--text)}
[data-testid="stMetric"]{background:linear-gradient(145deg,#152430,#101923);border:1px solid var(--line);padding:14px 16px;border-radius:13px;min-height:95px}[data-testid="stMetricLabel"]{color:var(--muted);font-weight:700;font-size:.78rem}[data-testid="stMetricValue"]{font-weight:800;letter-spacing:-.04em;font-size:1.65rem}
.stButton>button{border-radius:9px;min-height:42px;border:1px solid #314758;background:#1a2a37;color:var(--text);font-weight:800}.stButton>button[kind="primary"]{background:var(--green);border-color:var(--green);color:#062317}
.hero{padding:18px 20px;border:1px solid #2b4050;border-radius:16px;background:linear-gradient(110deg,#172b3a,#101923);margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;gap:12px}.title{font-size:1.5rem;font-weight:800;letter-spacing:-.05em}.sub{font-size:.76rem;color:var(--muted);margin-top:4px}.tag{border:1px solid #315343;background:#102b20;color:#7ee8b6;padding:7px 11px;border-radius:99px;font-size:.75rem;font-weight:800;white-space:nowrap}.box{padding:16px;border:1px solid var(--line);background:#111c26;border-radius:14px;margin:10px 0}.decision{font-size:1.55rem;font-weight:900;letter-spacing:-.04em}.muted{color:var(--muted);font-size:.84rem}.green{color:var(--green)}.red{color:var(--red)}.gold{color:var(--gold)}
@media(max-width:700px){.block-container{padding:.5rem .6rem 1rem}.hero{padding:13px}.title{font-size:1.15rem}.tag{font-size:.65rem}.decision{font-size:1.25rem}[data-testid="stMetricValue"]{font-size:1.25rem}}
</style>''', unsafe_allow_html=True)

# Automatic dashboard rerun every 5 seconds while the page remains open.
st_autorefresh(interval=5_000, key='nifty_sentinel_auto_refresh')
now = datetime.now(TZ)
st.markdown(f'''<div class="hero"><div><div class="title">◈ NIFTY SENTINEL</div><div class="sub">LIVE MARKET → STRATEGY → STRIKE → QUANTITY → SL / TARGET · AUTO-REFRESH 5s</div></div><div class="tag">GROWW CONNECTOR</div></div>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## Groww connection')
    auth = st.radio('Login method', ['Access token', 'API key + TOTP'], index=0)
    saved = ''
    try: saved = st.secrets.get('GROWW_ACCESS_TOKEN', '')
    except Exception: pass
    token = ''
    if auth == 'Access token':
        token = st.text_input('Groww access token', value=saved, type='password')
    else:
        api_key = st.text_input('Groww TOTP token / API key', type='password')
        totp_secret = st.text_input('TOTP secret', type='password')
        if st.button('Generate session token', type='primary', use_container_width=True):
            try:
                import pyotp
                from growwapi import GrowwAPI
                otp = pyotp.TOTP(totp_secret.strip()).now()
                result = GrowwAPI.get_access_token(api_key=api_key.strip(), totp=otp)
                if isinstance(result, dict):
                    result = result.get('access_token') or result.get('token')
                if not isinstance(result, str) or not result.strip():
                    raise RuntimeError('Groww did not return an access token.')
                st.session_state['gs_token'] = result.strip()
                st.success('Session token generated.')
            except Exception as e:
                st.error('Token generation failed. Check API key, TOTP secret and Groww approval.')
                st.caption(f'{type(e).__name__}: {str(e)[:160]}')
        token = st.session_state.get('gs_token', '')
    st.divider()
    capital = st.number_input('Trading capital (₹)', min_value=1000, max_value=100000000, value=150000, step=5000)
    risk_pct = st.select_slider('Risk budget per trade', options=[0.25,0.5,0.75,1.0], value=0.5, format_func=lambda x:f'{x:.2f}%')
    manual_lot_size = st.number_input('NIFTY lot size fallback (verify in Groww)', min_value=1, max_value=1000, value=65, step=1)
    st.caption('No orders are placed. Never put credentials in GitHub or chat.')

if not token:
    st.info('Groww se connect karne ke liye sidebar mein access token ya API key + TOTP choose kar.')
    st.stop()

HEADERS={'Accept':'application/json','Authorization':f'Bearer {token}','X-API-VERSION':'1.0'}
def api_get(path, params=None, timeout=15):
    r=requests.get(BASE+path,headers=HEADERS,params=params,timeout=timeout)
    try: body=r.json()
    except Exception: body={'message':r.text[:180]}
    if r.status_code != 200:
        err=body.get('error',{}) if isinstance(body,dict) else {}
        raise RuntimeError(f'HTTP {r.status_code} {err.get("code","")}: {err.get("message",body)}')
    if isinstance(body,dict) and body.get('status')=='FAILURE':
        err=body.get('error',{}); raise RuntimeError(f'{err.get("code","API_FAILURE")}: {err.get("message","Request failed")}')
    return body.get('payload',body) if isinstance(body,dict) else body

def normalize_candles(rows):
    """Normalize Groww candle rows; timestamps may be ISO strings or epoch seconds."""
    if not rows:
        return pd.DataFrame(columns=['Timestamp','Open','High','Low','Close','Volume','OpenInterest'])
    d = pd.DataFrame(rows)
    if d.shape[1] < 6:
        raise RuntimeError(f'Unexpected Groww candle row shape: {d.shape[1]} columns.')
    d = d.iloc[:, :7].copy()
    names = ['Timestamp','Open','High','Low','Close','Volume','OpenInterest'][:d.shape[1]]
    d.columns = names
    raw = d['Timestamp']
    raw_datetime = pd.api.types.is_datetime64_any_dtype(raw) or raw.map(lambda x: isinstance(x, (datetime, pd.Timestamp))).mean() > 0.8
    numeric = pd.to_numeric(raw, errors='coerce')
    if not raw_datetime and numeric.notna().mean() > 0.8:
        magnitude = numeric.dropna().abs().median()
        unit = 'ms' if magnitude > 1e11 else 's'
        d['Timestamp'] = pd.to_datetime(numeric, unit=unit, errors='coerce', utc=True).dt.tz_convert(TZ)
    else:
        ts = pd.to_datetime(raw, errors='coerce')
        if getattr(ts.dt, 'tz', None) is None:
            d['Timestamp'] = ts.dt.tz_localize(TZ, ambiguous='NaT', nonexistent='NaT')
        else:
            d['Timestamp'] = ts.dt.tz_convert(TZ)
    for c in ['Open','High','Low','Close','Volume']:
        if c not in d: d[c] = float('nan')
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['Timestamp','Open','High','Low','Close'])
    d = d.sort_values('Timestamp').drop_duplicates('Timestamp').reset_index(drop=True)
    return d

def get_candles():
    """Fetch 28 days in two <=14-day chunks; Groww limits 5-minute requests to 15 days."""
    from growwapi import GrowwAPI
    sdk = GrowwAPI(token)
    end = datetime.now(TZ).replace(tzinfo=None)
    start = end - timedelta(days=28)
    all_rows = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=14), end)
        response = sdk.get_historical_candles(
            exchange=sdk.EXCHANGE_NSE,
            segment=sdk.SEGMENT_CASH,
            groww_symbol='NSE-NIFTY',
            start_time=cursor.strftime('%Y-%m-%d %H:%M:%S'),
            end_time=chunk_end.strftime('%Y-%m-%d %H:%M:%S'),
            candle_interval=sdk.CANDLE_INTERVAL_MIN_5,
        )
        rows = response.get('candles', []) if isinstance(response, dict) else []
        all_rows.extend(rows)
        cursor = chunk_end
    d = normalize_candles(all_rows)
    if d.empty:
        raise RuntimeError('Groww returned no valid historical candles.')
    return d

def parse_ohlc(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    # Groww may return a string like {open: 149.50,high: 150.50,...} without quoted keys.
    out = {}
    for key, number in re.findall(r'(open|high|low|close)\s*:\s*(-?\d+(?:\.\d+)?)', value, flags=re.I):
        out[key.lower()] = float(number)
    return out

def cached_api_get(cache_key, path, params=None, ttl=5):
    """Small session cache prevents the 5-second UI rerun from hammering slower endpoints."""
    import time as _time
    key = hashlib.sha256((token + '|' + cache_key).encode()).hexdigest()[:24]
    entry = st.session_state.get('api_cache_' + key)
    now_epoch = _time.time()
    if entry and now_epoch - entry['at'] < ttl:
        return entry['value']
    value = api_get(path, params)
    st.session_state['api_cache_' + key] = {'at': now_epoch, 'value': value}
    return value

def generate_signal(candles, now, market_clock, spot_available):
    """Return a conservative signal from the latest fully closed candle only."""
    result = {'latest': None, 'fresh': False, 'direction': 0, 'signal': 'WAIT',
              'why': 'Live candles not verified', 'entry_spot': None,
              'stop_spot': None, 'target_spot': None}
    if candles is None or candles.empty or len(candles) < 60:
        result['why'] = 'Need at least 60 valid Groww candles. No signal generated.'
        return result
    d = indicators(candles)
    now_ts = pd.Timestamp(now)
    if d['Timestamp'].dt.tz is None:
        d['Timestamp'] = d['Timestamp'].dt.tz_localize(TZ)
    complete_rows = d[d['Timestamp'] + pd.Timedelta(minutes=5) <= now_ts]
    if complete_rows.empty:
        result['why'] = 'No fully completed 5-minute candle available yet.'
        return result
    latest = complete_rows.iloc[-1]
    result['latest'] = latest
    candle_time = latest.Timestamp
    age_min = (now_ts - candle_time).total_seconds() / 60
    fresh = candle_time.date() == now.date() and age_min >= 5 and age_min <= 10 and market_clock
    result['fresh'] = fresh
    if not fresh:
        result['why'] = f'Latest completed candle is stale or market is closed ({candle_time.strftime("%d %b %H:%M %Z")}). No live signal.'
        return result
    if not spot_available:
        result['why'] = 'Live NIFTY quote is unavailable. No signal generated.'
        return result
    if pd.isna(latest.PriorHigh12) or pd.isna(latest.PriorLow12) or pd.isna(latest.ATR) or latest.ATR <= 0:
        result['why'] = 'Indicators are not ready. No signal generated.'
        return result
    direction = 0
    if latest.Close > latest.PriorHigh12 and latest.EMA20 > latest.EMA50 and 52 <= latest.RSI <= 72:
        direction = 1
        result['signal'] = 'CE SETUP'
        result['why'] = 'Completed 5-minute close broke above prior 12-bar high with EMA20 > EMA50 and RSI confirmation.'
    elif latest.Close < latest.PriorLow12 and latest.EMA20 < latest.EMA50 and 28 <= latest.RSI <= 48:
        direction = -1
        result['signal'] = 'PE SETUP'
        result['why'] = 'Completed 5-minute close broke below prior 12-bar low with EMA20 < EMA50 and RSI confirmation.'
    else:
        result['why'] = 'No confirmed breakout/breakdown on the latest completed 5-minute candle.'
    result['direction'] = direction
    if direction:
        entry = float(latest.Close)
        atr = float(latest.ATR)
        result['entry_spot'] = entry
        result['stop_spot'] = entry - direction * atr
        result['target_spot'] = entry + direction * 1.5 * atr
    return result

def indicators(d):
    d=d.copy()
    d['EMA20']=d.Close.ewm(span=20,adjust=False).mean(); d['EMA50']=d.Close.ewm(span=50,adjust=False).mean()
    delta=d.Close.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs=gain/loss.replace(0,float('nan')); d['RSI']=(100-100/(1+rs)).fillna(50)
    d['PriorHigh12']=d.High.rolling(12).max().shift(1); d['PriorLow12']=d.Low.rolling(12).min().shift(1)
    prev=d.Close.shift(1); tr=pd.concat([d.High-d.Low,(d.High-prev).abs(),(d.Low-prev).abs()],axis=1).max(axis=1); d['ATR']=tr.ewm(alpha=1/14,adjust=False).mean()
    return d

# Market-hours guard (exchange holiday status additionally inferred from live data/candle freshness).
market_clock = now.weekday()<5 and time(9,15)<=now.time().replace(tzinfo=None)<time(15,30)
market_label='MARKET OPEN' if market_clock else 'MARKET CLOSED'
market_color='green' if market_clock else 'red'
spot=None; ohlc={}; chain_df=pd.DataFrame(); api_errors=[]
try:
    q=cached_api_get('ltp','/live-data/ltp',{'segment':'CASH','exchange_symbols':'NSE_NIFTY'},ttl=5)
    spot=float(q['NSE_NIFTY'])
except Exception as e: api_errors.append('Live quote: '+str(e))
try:
    q=cached_api_get('ohlc','/live-data/ohlc',{'segment':'CASH','exchange_symbols':'NSE_NIFTY'},ttl=5); ohlc=parse_ohlc(q.get('NSE_NIFTY',{}))
except Exception as e: api_errors.append('OHLC: '+str(e))

# UI reruns every 5 seconds; market quotes are cached for 5 seconds and candles refetched every 60 seconds.
refresh=st.button('↻ Refresh market + strategy',type='primary',use_container_width=True)
try:
    last_fetch=st.session_state.get('candles_fetch_epoch',0)
    import time as _time
    if refresh or 'candles_df' not in st.session_state or _time.time()-last_fetch>60:
        st.session_state['candles_df']=get_candles(); st.session_state['candles_fetch_epoch']=_time.time(); st.session_state['candles_fetched_at']=datetime.now(TZ).strftime('%H:%M:%S IST')
    candles=st.session_state['candles_df'].copy()
except Exception as e:
    candles=st.session_state.get('candles_df',pd.DataFrame())
    api_errors.append('Historical candles: '+str(e))

st.markdown(f'<div class="box"><div class="decision {market_color}">{market_label}</div><div class="muted">{now.strftime("%A, %d %b %Y · %H:%M:%S IST")} · NSE regular session 09:15–15:30 IST</div></div>',unsafe_allow_html=True)
if spot is not None:
    c1,c2,c3,c4=st.columns(4); c1.metric('NIFTY 50',f'{spot:,.2f}')
    for col,label,key in [(c2,'Day open','open'),(c3,'Day high','high'),(c4,'Day low','low')]:
        try: col.metric(label,f'{float(ohlc[key]):,.2f}')
        except Exception: col.metric(label,'—')
else:
    st.error('Live quote unavailable. No trade recommendation will be generated.')

# Signal only from the latest fully closed 5-minute candle.
signal_state = generate_signal(candles, now, market_clock, spot is not None)
latest = signal_state['latest']; fresh = signal_state['fresh']; signal = signal_state['signal']
why = signal_state['why']; direction = signal_state['direction']
entry_spot = signal_state['entry_spot']; stop_spot = signal_state['stop_spot']; target_spot = signal_state['target_spot']

st.markdown('## Trade decision')
if not market_clock:
    st.markdown('<div class="box"><div class="decision red">NO TRADE — MARKET CLOSED</div><div class="muted">App will not show a new actionable entry outside regular NSE market hours.</div></div>',unsafe_allow_html=True)
elif spot is None:
    st.markdown('<div class="box"><div class="decision red">NO TRADE — DATA DISCONNECTED</div><div class="muted">Reconnect Groww and refresh. No prices are fabricated.</div></div>',unsafe_allow_html=True)
elif not fresh:
    st.markdown(f'<div class="box"><div class="decision gold">NO TRADE — WAIT</div><div>{why}</div></div>',unsafe_allow_html=True)
elif not direction:
    st.markdown(f'<div class="box"><div class="decision gold">NO TRADE — WAIT</div><div>{why}</div><div class="muted">Latest 5m candle: {latest.Timestamp.strftime("%H:%M:%S IST")} · RSI {latest.RSI:.1f}</div></div>',unsafe_allow_html=True)
else:
    st.markdown(f'<div class="box"><div class="decision {"green" if direction>0 else "red"}">{signal}</div><div>{why}</div><div class="muted">Underlying reference entry {entry_spot:,.2f} · invalidation {stop_spot:,.2f} · target {target_spot:,.2f}. These are index levels, not option premium levels.</div></div>',unsafe_allow_html=True)

# Option chain for current expiry; only provide a contract/quantity if live chain includes premium and lot size.
expiries=[]
today=now.date()
try:
    for offset in [0,1]:
        month=(today.month-1+offset)%12+1; year=today.year+(today.month-1+offset)//12
        payload=cached_api_get(f'expiries-{year}-{month}','/historical/expiries',{'exchange':'NSE','underlying_symbol':'NIFTY','year':year,'month':month},ttl=3600)
        for item in payload.get('expiries',[]):
            try:
                dt=date.fromisoformat(str(item)[:10])
                if dt>=today and dt not in expiries: expiries.append(dt)
            except Exception: pass
except Exception as e: api_errors.append('Expiry list: '+str(e))
expiry=st.selectbox('Option expiry',sorted(expiries),format_func=lambda x:x.strftime('%d %b %Y')) if expiries else None
if expiry:
    try:
        payload=cached_api_get('chain-'+expiry.isoformat(),'/option-chain/exchange/NSE/underlying/NIFTY',{'expiry_date':expiry.isoformat()},ttl=15)
        strikes=payload.get('strikes',{})
        rows=[]
        for strike,sides in strikes.items():
            try: sn=float(strike)
            except Exception: continue
            row={'Strike':sn}
            for side in ['CE','PE']:
                c=(sides or {}).get(side) or {}
                row[f'{side} LTP']=pd.to_numeric(c.get('ltp'),errors='coerce')
                row[f'{side} OI']=c.get('open_interest'); row[f'{side} Volume']=c.get('volume')
                row[f'{side} Symbol']=c.get('trading_symbol'); row[f'{side} Lot size']=c.get('lot_size') or c.get('lotSize')
                greeks=c.get('greeks') or {}
                row[f'{side} Delta']=greeks.get('delta'); row[f'{side} Theta']=greeks.get('theta'); row[f'{side} IV']=greeks.get('iv')
            rows.append(row)
        chain_df=pd.DataFrame(rows).sort_values('Strike') if rows else pd.DataFrame()
    except Exception as e: api_errors.append('Option chain: '+str(e))

st.markdown('## Exact contract & quantity')
if direction and fresh and market_clock and not chain_df.empty and spot is not None:
    side='CE' if direction>0 else 'PE'
    chain_df['dist']=(chain_df.Strike-spot).abs(); contract=chain_df.sort_values('dist').iloc[0]
    premium=contract.get(f'{side} LTP'); sym=contract.get(f'{side} Symbol'); lot_raw=contract.get(f'{side} Lot size')
    try: lot=int(lot_raw) if pd.notna(lot_raw) and int(lot_raw)>0 else 0
    except Exception: lot=0
    if lot <= 0 and sym and expiry:
        try:
            from growwapi import GrowwAPI
            sdk=GrowwAPI(token)
            groww_symbol=f'NSE-NIFTY-{expiry.strftime("%d%b%y")}-{int(contract.Strike)}-{side}'
            inst=sdk.get_instrument_by_groww_symbol(groww_symbol=groww_symbol)
            lot=int(inst.get('lot_size',0) or 0) if isinstance(inst,dict) else 0
        except Exception:
            lot=0
    if lot <= 0:
        lot=int(manual_lot_size)
        lot_source='manual fallback — verify contract lot size in Groww'
    else:
        lot_source='Groww instrument master / option-chain data'
    if pd.notna(premium) and float(premium)>0 and lot>0:
        # Conservative illustrative premium SL: 20%; target 1.5R; quantity rounded down to full lots.
        prem=float(premium); sl=prem*0.80; target=prem+(prem-sl)*1.5
        risk_cash=capital*risk_pct/100; per_unit=prem-sl
        lots=max(0,math.floor(risk_cash/(per_unit*lot)))
        qty=lots*lot; planned_loss=qty*per_unit; target_profit=qty*(target-prem)
        a,b,c,dcol=st.columns(4); a.metric('Contract',str(sym or f'NIFTY {contract.Strike:.0f} {side}')); b.metric('Entry premium',f'₹{prem:.2f}'); c.metric('Stop-loss',f'₹{sl:.2f}'); dcol.metric('Target',f'₹{target:.2f}')
        a,b,c,dcol=st.columns(4); a.metric('Lots',str(lots)); b.metric('Quantity',str(qty)); c.metric('Planned loss',f'₹{planned_loss:,.0f}'); dcol.metric('Target profit',f'₹{target_profit:,.0f}')
        if lots==0: st.warning('NO TRADE: one lot exceeds your risk budget at this premium/stop. Do not round quantity up.')
        else: st.warning(f'Research signal only. Lot size source: {lot_source}. Premium SL/target use a 20% stop and 1.5R target assumption; confirm bid/ask, liquidity, charges and lot size in Groww before manual entry.')
    else:
        st.warning('Signal exists, but option premium is missing/invalid. No quantity recommendation shown.')
elif direction and chain_df.empty:
    st.warning('Index setup exists, but option-chain data is unavailable. No exact strike/quantity will be invented.')
elif not chain_df.empty and spot is not None:
    atm=chain_df.iloc[(chain_df.Strike-spot).abs().argsort()[:1]]
    st.caption('Option chain is available, but no confirmed live setup. No BUY instruction.')
    show=chain_df.copy(); show['Distance']=abs(show.Strike-spot); show=show.nsmallest(15,'Distance')
    cols=['Strike','CE LTP','CE OI','CE Volume','CE Delta','CE Theta','CE IV','PE LTP','PE OI','PE Volume','PE Delta','PE Theta','PE IV']
    st.dataframe(show[cols],use_container_width=True,hide_index=True)
else:
    st.info('Option-chain data not available. Live NIFTY quote and strategy status are shown independently.')

with st.expander('Connection diagnostics'):
    st.write('Last candle fetch:',st.session_state.get('candles_fetched_at','not fetched'))
    if not candles.empty: st.write('Latest candle:',str(candles.iloc[-1]['Timestamp']))
    if api_errors:
        for err in api_errors: st.error(err)
    else: st.success('No API errors in this refresh.')
    st.caption('UI refresh: 5 seconds. LTP/OHLC cache: 5 seconds; option chain: 15 seconds; candles: 60 seconds. Signal uses only the latest fully closed 5-minute candle and regular NSE hours. Holiday detection is inferred from live data/candle freshness. Index levels are not option-premium levels. Manual execution only.')

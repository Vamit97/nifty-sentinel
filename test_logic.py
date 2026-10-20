import ast
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

path='app.py'
tree=ast.parse(open(path,encoding='utf-8').read())
want={'normalize_candles','indicators','generate_signal','parse_ohlc'}
funcs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in want]
ns={'pd':pd,'datetime':datetime,'TZ':ZoneInfo('Asia/Kolkata'),'timedelta':timedelta,'re':__import__('re')}
exec(compile(ast.Module(body=funcs,type_ignores=[]),path,'exec'),ns)

# Epoch timestamps must decode as seconds, not nanoseconds.
base=int(datetime(2026,10,20,9,15,tzinfo=ZoneInfo('Asia/Kolkata')).timestamp())
d=ns['normalize_candles']([[base,25000,25010,24990,25005,100],[base+300,25005,25020,25000,25015,120]])
assert len(d)==2 and d.Timestamp.iloc[0].year==2026 and d.Timestamp.iloc[0].hour==9, d
assert str(d.Timestamp.dt.tz)=='Asia/Kolkata'

# Strategy refuses to issue signals when the market is closed, even with enough candles.
start=datetime(2026,10,20,9,15,tzinfo=ZoneInfo('Asia/Kolkata'))
rows=[]
for i in range(80):
    px=25000+i*2
    rows.append([start+timedelta(minutes=5*i),px,px+4,px-3,px+2,100])
c=ns['normalize_candles'](rows)
r=ns['generate_signal'](c, datetime(2026,10,20,16,0,tzinfo=ZoneInfo('Asia/Kolkata')), False, True)
assert r['direction']==0 and not r['fresh'] and r['signal']=='WAIT', r

# Stale historical data must not produce a signal during the market session.
r=ns['generate_signal'](c, datetime(2026,10,20,14,0,tzinfo=ZoneInfo('Asia/Kolkata')), True, True)
assert r['direction']==0 and r['fresh'], r
# Previous-day candles must be rejected during current market hours.
old_start=datetime(2026,10,19,9,15,tzinfo=ZoneInfo('Asia/Kolkata'))
old_rows=[]
for i in range(80):
    px=25000+i*2
    old_rows.append([old_start+timedelta(minutes=5*i),px,px+4,px-3,px+2,100])
old_c=ns['normalize_candles'](old_rows)
r=ns['generate_signal'](old_c, datetime(2026,10,20,14,0,tzinfo=ZoneInfo('Asia/Kolkata')), True, True)
assert r['direction']==0 and not r['fresh'], r
ohlc=ns['parse_ohlc']('{open: 24900.5,high: 25020,low: 24880,close: 24980.25}')
assert ohlc == {'open':24900.5,'high':25020.0,'low':24880.0,'close':24980.25}, ohlc
print('PASS: epoch timestamps, timezone conversion, market/stale guards, WAIT logic, Groww OHLC parsing')

# backend/ict_detector.py
# Lightweight ICT detector (Order Blocks, FVG, MSB, Liquidity sweep)
# This is a heuristic detector intended to be deterministic and audit-able.
# It stores detected candidates to a small JSON/SQLite log for stats and learning.

import math, time, json, sqlite3, os
from typing import List, Dict, Any

DB_PATH = os.getenv("ICT_DB_PATH", "/tmp/ict_events.db")

def _ensure_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        ts INTEGER,
        kind TEXT,
        details TEXT,
        confidence REAL,
        resolved INTEGER DEFAULT 0,
        outcome TEXT DEFAULT NULL
    )""")
    conn.commit()
    conn.close()

def log_event(symbol: str, kind: str, details: Dict[str,Any], confidence: float=0.6):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO events (symbol, ts, kind, details, confidence) VALUES (?,?,?,?,?)",
                 (symbol, int(time.time()), kind, json.dumps(details), float(confidence)))
    conn.commit()
    conn.close()

def get_events(symbol: str, since_ts: int=0):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT id, ts, kind, details, confidence, resolved, outcome FROM events WHERE symbol=? AND ts>=? ORDER BY ts DESC",
                       (symbol, since_ts))
    rows = cur.fetchall()
    conn.close()
    out=[]
    for r in rows:
        out.append({"id": r[0], "ts": r[1], "kind": r[2], "details": json.loads(r[3]), "confidence": r[4], "resolved": bool(r[5]), "outcome": r[6]})
    return out

def ack_event(event_id:int, outcome:str):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    # update resolved and outcome
    conn.execute("UPDATE events SET resolved=1, outcome=? WHERE id=?",(outcome,event_id))
    # simple confidence adjustment: read, then update similar-kind outstanding events by small delta
    cur = conn.execute("SELECT kind, confidence FROM events WHERE id=?", (event_id,))
    row = cur.fetchone()
    if row:
        kind, conf = row
        delta = 0.05 if outcome=="win" else -0.07
        # update last 50 un-resolved same-kind events by adjusting their confidence
        conn.execute("UPDATE events SET confidence = CASE WHEN confidence + ? > 1.0 THEN 1.0 WHEN confidence + ? < 0.01 THEN 0.01 ELSE confidence + ? END WHERE symbol=? AND kind=? AND resolved=0",
                     (delta, delta, delta, get_symbol_by_event(conn,event_id), kind))
    conn.commit()
    conn.close()
    return True

def get_symbol_by_event(conn, event_id):
    cur = conn.execute("SELECT symbol FROM events WHERE id=?", (event_id,))
    r = cur.fetchone()
    return r[0] if r else None

# ---------- detection helpers ----------
def simple_swing_points(candles: List[Dict[str,Any]], window:int=3):
    swings=[]
    n=len(candles)
    for i in range(window, n-window):
        is_high = all(candles[i]['high'] > candles[j]['high'] for j in range(i-window, i)) and all(candles[i]['high'] > candles[j]['high'] for j in range(i+1, i+1+window))
        if is_high:
            swings.append({"type":"high","index":i,"price":candles[i]['high']})
        is_low = all(candles[i]['low'] < candles[j]['low'] for j in range(i-window, i)) and all(candles[i]['low'] < candles[j]['low'] for j in range(i+1, i+1+window))
        if is_low:
            swings.append({"type":"low","index":i,"price":candles[i]['low']})
    return swings

def detect_order_blocks(candles: List[Dict[str,Any]], lookback:int=60) -> List[Dict[str,Any]]:
    ob_list=[]
    n=len(candles)
    start = max(3, n - lookback)
    for i in range(start, n-2):
        o=candles[i]['open']; c=candles[i]['close']; prev=candles[i-1]['close']
        body = abs(c - o)
        if body> (0.4 * (candles[i]['high']-candles[i]['low'])) and c > o and c > prev * 1.005:
            low=min(candles[i-1]['open'], candles[i-1]['close'], candles[i-1]['low'])
            high=max(candles[i-1]['open'], candles[i-1]['close'], candles[i-1]['high'])
            ob = {"side":"bull","start_index":i-1,"end_index":i-1,"low":low,"high":high, "reason":"strong_bull_move"}
            ob_list.append(ob)
        if body> (0.4 * (candles[i]['high']-candles[i]['low'])) and c < o and c < prev * 0.995:
            low=min(candles[i-1]['open'], candles[i-1]['close'], candles[i-1]['low'])
            high=max(candles[i-1]['open'], candles[i-1]['close'], candles[i-1]['high'])
            ob = {"side":"bear","start_index":i-1,"end_index":i-1,"low":low,"high":high, "reason":"strong_bear_move"}
            ob_list.append(ob)
    return ob_list

def detect_fvg(candles: List[Dict[str,Any]], lookback:int=60) -> List[Dict[str,Any]]:
    fvg=[]
    n=len(candles)
    for i in range(max(2, n-lookback), n-1):
        a_high=candles[i-1]['high']; b_low=candles[i+1]['low']
        if b_low > a_high:
            fvg.append({"start_index":i-1,"end_index":i+1,"low":a_high,"high":b_low})
    return fvg

def detect_msb(candles: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    swings = simple_swing_points(candles, window=3)
    if not swings: return []
    last = swings[-1]
    out=[]
    if last['type']=='high':
        prev_high = None
        for s in reversed(swings[:-1]):
            if s['type']=='high':
                prev_high = s
                break
        if prev_high and last['price'] > prev_high['price']:
            out.append({"type":"MSB_bull","index": last['index'], "price": last['price']})
    if last['type']=='low':
        prev_low = None
        for s in reversed(swings[:-1]):
            if s['type']=='low':
                prev_low = s
                break
        if prev_low and last['price'] < prev_low['price']:
            out.append({"type":"MSB_bear","index": last['index'], "price": last['price']})
    return out

def detect_liquidity_sweeps(candles: List[Dict[str,Any]], lookback:int=60) -> List[Dict[str,Any]]:
    sweeps=[]
    n=len(candles)
    swings = simple_swing_points(candles, window=3)
    swing_highs = [s for s in swings if s['type']=='high']
    swing_lows = [s for s in swings if s['type']=='low']
    last_high = swing_highs[-1]['price'] if swing_highs else None
    last_low = swing_lows[-1]['price'] if swing_lows else None
    for i in range(max(1,n-lookback), n):
        if last_high and candles[i]['high'] > last_high * 1.0015:
            sweeps.append({"side":"up","index":i,"price":candles[i]['high']})
        if last_low and candles[i]['low'] < last_low * 0.9985:
            sweeps.append({"side":"down","index":i,"price":candles[i]['low']})
    return sweeps

def detect_all(candles: List[Dict[str,Any]], symbol:str="SYM") -> Dict[str,Any]:
    overlays = {}
    ob = detect_order_blocks(candles, lookback=120)
    fvg = detect_fvg(candles, lookback=120)
    msb = detect_msb(candles)
    sweeps = detect_liquidity_sweeps(candles, lookback=120)

    overlays['order_blocks'] = ob
    overlays['fvg'] = fvg
    overlays['msb'] = msb
    overlays['sweeps'] = sweeps

    candidates=[]
    if ob:
        last_ob = ob[-1]
        side = "long" if last_ob['side']=='bull' else "short"
        entry = (last_ob['low']+last_ob['high'])/2
        stop = last_ob['low'] - (abs(last_ob['high']-last_ob['low']) * 0.5) if side=='long' else last_ob['high'] + (abs(last_ob['high']-last_ob['low']) * 0.5)
        target = None
        if msb:
            target = msb[-1]['price']
        else:
            last_close = candles[-1]['close']
            target = last_close + (last_close - stop) * 2 if side=='long' else last_close - (stop - last_close) * 2
        rr = abs((target - entry) / (entry - stop)) if entry!=stop else 0.0
        cand = {"symbol":symbol, "side":side, "entry":round(entry,4), "stop":round(stop,4), "target":round(target,4), "rr":round(rr,2), "reason":"OB_primary"}
        candidates.append(cand)
        log_event(symbol, "OB_candidate", cand, confidence=0.6)
    for s in sweeps:
        log_event(symbol, "sweep", s, confidence=0.45)
    return {"overlays":overlays, "candidates":candidates}
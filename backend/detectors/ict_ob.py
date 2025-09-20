from typing import List, Dict, Any
from datetime import datetime, timezone

def detect_order_blocks(bars: List[Dict[str, Any]], symbol: str = "UNKNOWN", tf: str = "1m") -> List[Dict]:
    candidates = []
    if not bars or len(bars) < 4:
        return candidates

    for i in range(2, len(bars)-1):
        strong = bars[i-1]
        pull = bars[i]
        nextc = bars[i+1]

        if strong['close'] < strong['open']:
            body = abs(strong['open'] - strong['close'])
            high_low_range = max(1e-6, strong['high'] - strong['low'])
            if body / high_low_range > 0.5:
                zone_high = max(strong['open'], strong['close'])
                zone_low = min(strong['open'], strong['close'])
                if pull['low'] <= zone_high and nextc['close'] > nextc['open']:
                    entry_price = nextc['open']
                    stop_price = strong['high'] + 0.0005
                    targets = [entry_price + (entry_price - stop_price) * r for r in [0.5, 1.0, 1.5]]
                    cand = {
                        "candidate_id": f"cand_{symbol}_{tf}_{i}_{int(datetime.now(timezone.utc).timestamp())}",
                        "symbol": symbol,
                        "tf": tf,
                        "pattern": "OrderBlock",
                        "patterns": ["ict_ob_v1"],
                        "entry_ts": nextc.get('ts'),
                        "entry_price": round(entry_price, 6),
                        "stop_price": round(stop_price, 6),
                        "targets": [round(t, 6) for t in targets],
                        "zone": [round(zone_low, 6), round(zone_high, 6)],
                        "confidence": 0.5,
                        "evidence": ["strong_bear_body","pullback_touch","bull_rejection"],
                        "features": {"body": round(body,6), "range": round(high_low_range,6)},
                        "provenance": {"detectors":["ict_ob_v1"], "model_version":"det-v1"},
                        "metadata": {},
                        "ts": datetime.now(timezone.utc).isoformat()
                    }
                    candidates.append(cand)

        if strong['close'] > strong['open']:
            body = abs(strong['open'] - strong['close'])
            high_low_range = max(1e-6, strong['high'] - strong['low'])
            if body / high_low_range > 0.5:
                zone_high = max(strong['open'], strong['close'])
                zone_low = min(strong['open'], strong['close'])
                if pull['high'] >= zone_low and nextc['close'] < nextc['open']:
                    entry_price = nextc['open']
                    stop_price = strong['low'] - 0.0005
                    targets = [entry_price - (stop_price - entry_price) * r for r in [0.5, 1.0, 1.5]]
                    cand = {
                        "candidate_id": f"cand_{symbol}_{tf}_{i}_{int(datetime.now(timezone.utc).timestamp())}",
                        "symbol": symbol,
                        "tf": tf,
                        "pattern": "OrderBlock",
                        "patterns": ["ict_ob_v1"],
                        "entry_ts": nextc.get('ts'),
                        "entry_price": round(entry_price,6),
                        "stop_price": round(stop_price,6),
                        "targets": [round(t,6) for t in targets],
                        "zone": [round(zone_low,6), round(zone_high,6)],
                        "confidence": 0.5,
                        "evidence": ["strong_bull_body","pullback_touch","bear_rejection"],
                        "features": {"body": round(body,6), "range": round(high_low_range,6)},
                        "provenance": {"detectors":["ict_ob_v1"], "model_version":"det-v1"},
                        "metadata": {},
                        "ts": datetime.now(timezone.utc).isoformat()
                    }
                    candidates.append(cand)
    return candidates
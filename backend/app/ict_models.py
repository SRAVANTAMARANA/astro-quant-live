def detect_bos(candles):
    signals = []
    for i in range(2, len(candles)):
        prev, cur = candles[i-1], candles[i]
        if cur["h"] > prev["h"] and cur["c"] > prev["h"]:
            signals.append({"time": cur["t"], "type": "bos_bull", "price": cur["c"]})
        if cur["l"] < prev["l"] and cur["c"] < prev["l"]:
            signals.append({"time": cur["t"], "type": "bos_bear", "price": cur["c"]})
    return signals

def detect_choch(candles):
    signals = []
    return signals

def detect_sessions():
    return {"london":"07:00-10:00","newyork":"13:00-16:00","asia":"00:00-03:00"}

def compute_all_ict_models(candles):
    return {
        "bos": detect_bos(candles),
        "choch": detect_choch(candles),
        "sessions": detect_sessions()
    }

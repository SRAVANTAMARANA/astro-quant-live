def detect_turtle_soup(candles):
    signals = []
    for i in range(2, len(candles)):
        a, b, c = candles[i-2], candles[i-1], candles[i]
        if (b['l'] < a['l']) and (c['c'] > b['o']):
            signals.append({"time": c['t'], "type": "turtle_bull", "price": c['c']})
        if (b['h'] > a['h']) and (c['c'] < b['o']):
            signals.append({"time": c['t'], "type": "turtle_bear", "price": c['c']})
    return signals

def detect_fvg(candles):
    signals = []
    for i in range(1, len(candles)-1):
        prev, cur = candles[i-1], candles[i]
        if cur['l'] > prev['h']:
            signals.append({"time": cur['t'], "type": "fvg_up"})
        if cur['h'] < prev['l']:
            signals.append({"time": cur['t'], "type": "fvg_down"})
    return signals

def detect_order_blocks(candles):
    signals = []
    return signals  # stub for now

def compute_all_signals(candles):
    return {
        "turtle": detect_turtle_soup(candles),
        "fvg": detect_fvg(candles),
        "order_blocks": detect_order_blocks(candles),
    }

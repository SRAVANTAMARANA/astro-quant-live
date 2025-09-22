import random

def generate_narrative(signals, symbol):
    msg = [f"Mentor Report for {symbol}:"]
    if signals.get("bos"): msg.append(f"- BOS: {len(signals['bos'])}")
    if signals.get("choch"): msg.append(f"- CHoCH: {len(signals['choch'])}")
    if signals.get("turtle"): msg.append(f"- Turtle: {len(signals['turtle'])}")
    if signals.get("fvg"): msg.append(f"- FVG: {len(signals['fvg'])}")
    if signals.get("order_blocks"): msg.append(f"- OB: {len(signals['order_blocks'])}")
    msg.append("Bias: " + random.choice(["Bullish","Bearish","Neutral"]))
    return "\n".join(msg)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from detectors.ict_ob import detect_order_blocks

router = APIRouter(prefix="/api/detect", tags=["detect"])

class Bar(BaseModel):
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

class BarsReq(BaseModel):
    symbol: str
    tf: str
    bars: List[Bar]

STORE: List[Dict[str, Any]] = []

@router.post("/ob")
async def detect_ob(req: BarsReq):
    try:
        bars = [b.dict() for b in req.bars]
        candidates = detect_order_blocks(bars, symbol=req.symbol, tf=req.tf)
        for c in candidates:
            STORE.append(c)
        return {"ok": True, "candidates": candidates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates")
async def list_candidates(symbol: str = None):
    if symbol:
        return [c for c in STORE if c.get("symbol") == symbol]
    return STORE
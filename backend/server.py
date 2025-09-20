from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AstraQuant Backend (ICT)")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from api.detect_ob import router as detect_router
    app.include_router(detect_router)
except Exception as e:
    @app.get("/_import_error")
    async def import_error():
        return {"ok": False, "error": str(e)}

@app.get("/health")
async def health():
    return {"status": "ok"}
"""FastAPI entry point for the CVD simulation demonstrator."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.simulation import router as simulation_router
from app.config import settings
from app.middleware.rate_limit import limiter

app = FastAPI(title="Machado CVD Simulation API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(simulation_router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "machado-cvd-simulation"}


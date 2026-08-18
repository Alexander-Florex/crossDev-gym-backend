from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.routers import (
    attendance,
    auth,
    bookings,
    classes,
    memberships,
    reports,
    routines,
    tenants,
    users,
)
from app.utils.rate_limit import limiter

settings = get_settings()

app = FastAPI(title="CrossDEV Gym Platform API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(memberships.router)
app.include_router(classes.router)
app.include_router(bookings.router)
app.include_router(routines.router)
app.include_router(attendance.router)
app.include_router(reports.router)


@app.get("/")
async def health_check():
    return {"status": "ok"}

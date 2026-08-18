import time

from fastapi import FastAPI, Request
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
from app.utils.logging import configure_logging, get_logger
from app.utils.rate_limit import limiter

settings = get_settings()

configure_logging()
logger = get_logger(__name__)

TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Autenticación: alta de gimnasio (tenant) + admin, login, refresh de "
        "tokens y perfil del usuario autenticado.",
    },
    {
        "name": "users",
        "description": "Gestión de usuarios del gimnasio: personal trainers y alumnos.",
    },
    {"name": "tenants", "description": "Datos del gimnasio (tenant) actual."},
    {
        "name": "memberships",
        "description": "Membresías de los alumnos: alta, renovación, suspensión y baja.",
    },
    {"name": "classes", "description": "Clases del gimnasio, cupos y disponibilidad."},
    {"name": "bookings", "description": "Reservas de alumnos a clases."},
    {
        "name": "routines",
        "description": "Rutinas de entrenamiento armadas por el personal trainer, con "
        "exportación a PDF.",
    },
    {"name": "attendance", "description": "Registro de asistencia (check-in) de alumnos."},
    {
        "name": "reports",
        "description": "Reportes básicos del gimnasio para el panel de administración.",
    },
]

app = FastAPI(
    title="CrossDEV Gym Platform API",
    description=(
        "API REST del backend de CrossDEV Gym Platform, una plataforma SaaS para "
        "gimnasios. Expone los endpoints que consumen el panel web, la app móvil y "
        "el resto de los clientes de la plataforma."
    ),
    version="0.1.0",
    openapi_tags=TAGS_METADATA,
)

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(memberships.router)
app.include_router(classes.router)
app.include_router(bookings.router)
app.include_router(routines.router)
app.include_router(attendance.router)
app.include_router(reports.router)


@app.get("/", summary="Health check", description="Verifica que la API esté levantada.")
async def health_check():
    return {"status": "ok"}

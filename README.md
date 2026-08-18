# CrossDEV Gym Platform — Backend

Backend de CrossDEV Gym Platform, una plataforma SaaS vertical para gimnasios. Expone la API REST que consumen el panel web (React), la app móvil (Flutter) y cualquier otro cliente de la plataforma.

## Stack

- **Python 3.12+** / **FastAPI** (async)
- **PostgreSQL 16** + **SQLAlchemy 2.x** (async, `asyncpg`) + **Alembic**
- **JWT** (access + refresh) para autenticación
- **Redis** — rate limiting (`slowapi`) y base para tareas en background
- **Pydantic v2** para validación y schemas
- **structlog** para logging estructurado (JSON en producción, consola en desarrollo)
- **pytest** + **pytest-asyncio** + **httpx** para testing
- **ruff** para lint/format

## Arquitectura

Multi-tenant: una sola base de datos, cada gimnasio es un `tenant_id`. El filtro por tenant está centralizado en `app/repositories/base.py` (`TenantScopedRepository`) para que ningún query pueda "olvidarse" de filtrar.

Roles (RBAC), validados siempre en backend:

- `super_admin` — CrossDEV interno
- `admin` — administrador del gimnasio
- `trainer` — personal trainer
- `student` — alumno / cliente

Planes comerciales: `basic` y `premium` (campo `plan_type` en `Tenant`). Este backend implementa el plan **basic** completo: usuarios, membresías, clases, reservas, rutinas con PDF, asistencia y reportes. El plan **premium** (chat en tiempo real, Mercado Pago, IA, notificaciones push, app móvil) todavía no está implementado.

```
app/
├── main.py            # FastAPI app, middlewares, routers
├── config.py           # Settings (Pydantic BaseSettings)
├── database.py          # Engine async, sessionmaker, Base
├── dependencies.py       # get_db, get_current_user, require_role, get_tenant
├── models/              # SQLAlchemy models
├── schemas/              # Pydantic request/response
├── routers/              # Endpoints por dominio (/api/v1/...)
├── services/              # Lógica de negocio
├── repositories/           # TenantScopedRepository (filtro tenant centralizado)
└── utils/                # security, pagination, pdf, logging, rate_limit
```

## Requisitos

- Python 3.12+
- Docker (para Postgres + Redis locales)

## Levantar el entorno

```bash
# 1. Clonar y entrar al repo
git clone https://github.com/Alexander-Florex/crossDev-gym-backend.git
cd crossDev-gym-backend

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash) / .venv\Scripts\activate en cmd
pip install -e ".[dev]"

# 3. Variables de entorno
cp .env.example .env

# 4. Levantar PostgreSQL + Redis
docker compose up -d

# 5. Crear la base de datos de test (además de la principal, que ya crea docker-compose)
docker exec crossdev-gym-postgres psql -U crossdev -d crossdev_gym -c "CREATE DATABASE crossdev_gym_test;"

# 6. Aplicar migraciones
alembic upgrade head

# 7. Levantar el servidor
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`, con documentación interactiva en `http://localhost:8000/docs`.

## Tests

Los tests corren contra una base de datos Postgres real (no se mockea la DB):

```bash
pytest -v
```

## Migraciones

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

## Lint

```bash
ruff check .
ruff format .
```

## Endpoints principales

Todos bajo `/api/v1`:

| Recurso | Prefijo | Notas |
|---|---|---|
| Auth | `/auth` | register, login, refresh, me — rate limited |
| Users | `/users` | CRUD de trainers y alumnos, solo admin gestiona |
| Tenants | `/tenants/me` | Ver/editar el gimnasio propio |
| Memberships | `/memberships` | Membresías de alumnos |
| Classes | `/classes` | Clases y cupos |
| Bookings | `/bookings` | Reservas (manuales o self-booking) |
| Routines | `/routines` | Rutinas + `/{id}/pdf` para descarga |
| Attendance | `/attendance` | Check-in |
| Reports | `/reports/overview` | Contadores generales, solo admin |

## Seguridad

- Rate limiting en endpoints de autenticación (Redis-backed, vía `slowapi`)
- Audit log (`AuditLog`) de las acciones mutantes principales: quién, qué, cuándo, desde qué IP
- `hashed_password` nunca se expone en responses
- Aislamiento estricto entre tenants (cubierto por tests)
- Soft delete en `User` y `Message`

## CI

GitHub Actions (`.github/workflows/ci.yml`) corre en cada push/PR a `main`: lint con ruff, migración contra Postgres real y suite de tests completa, con Postgres y Redis como servicios del job.

# CLAUDE.md — crossdev-gym-backend

## Proyecto

CrossDEV Gym Platform: plataforma SaaS vertical para gimnasios.
Tres repos independientes (backend, web React, mobile Flutter) consumen la misma API.
Este repo es el backend — punto central de reglas de negocio, autenticación, autorización, persistencia e integraciones.

## Stack confirmado

- **Lenguaje:** Python 3.12+
- **Framework:** FastAPI (async, OpenAPI automático, WebSocket nativo)
- **Base de datos:** PostgreSQL 16
- **ORM:** SQLAlchemy 2.x (async con asyncpg)
- **Migraciones:** Alembic
- **Autenticación:** JWT (access + refresh tokens)
- **Background tasks:** Celery + Redis (o ARQ si se decide async puro)
- **WebSockets:** FastAPI nativo (chat en tiempo real)
- **Validación:** Pydantic v2
- **Testing:** pytest + pytest-asyncio + httpx (AsyncClient)

## Multi-tenancy

Base de datos única compartida con `tenant_id` en cada tabla.
Cada gimnasio es un tenant. Las queries SIEMPRE filtran por tenant_id.
Implementar filtro a nivel de ORM/session para que ningún endpoint pueda olvidarlo.

## Planes comerciales

Dos planes: `basic` y `premium`. Se controlan con un campo `plan_type` en la tabla Tenant.
- **Básico:** panel web admin, gestión de usuarios/personal trainers/clientes, membresías, clases, reservas manuales, rutinas con PDF, asistencia, reportes básicos. NO incluye: app móvil, chat, pagos integrados, IA, landing, notificaciones push.
- **Premium:** todo lo del básico + app Flutter, chat en tiempo real, Mercado Pago, IA, landing con captación, notificaciones push, dashboard avanzado.

Los endpoints premium deben verificar `tenant.plan_type` antes de responder. Retornar 403 con mensaje claro si el plan no lo permite.

## Estructura de carpetas

```
crossdev-gym-backend/
├── alembic/                  # Migraciones
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, startup/shutdown, middleware
│   ├── config.py              # Settings con Pydantic BaseSettings
│   ├── database.py            # Engine, SessionLocal, Base
│   ├── dependencies.py        # Deps comunes (get_db, get_current_user, get_tenant)
│   ├── middleware/
│   │   ├── tenant.py          # Middleware/dep que inyecta tenant_id
│   │   └── auth.py            # Middleware JWT
│   ├── models/                # SQLAlchemy models (1 archivo por dominio)
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── membership.py
│   │   ├── class_.py
│   │   ├── booking.py
│   │   ├── routine.py
│   │   ├── attendance.py
│   │   ├── chat.py
│   │   ├── payment.py
│   │   └── audit.py
│   ├── schemas/               # Pydantic schemas (request/response)
│   │   └── (mismo patrón que models)
│   ├── routers/               # Endpoints agrupados por dominio
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── memberships.py
│   │   ├── classes.py
│   │   ├── bookings.py
│   │   ├── routines.py
│   │   ├── attendance.py
│   │   ├── chat.py
│   │   ├── payments.py
│   │   ├── reports.py
│   │   └── ai.py
│   ├── services/              # Lógica de negocio (1 por dominio)
│   │   └── (mismo patrón)
│   ├── utils/
│   │   ├── security.py        # Hashing, JWT encode/decode
│   │   ├── pagination.py      # Paginación estándar
│   │   └── pdf.py             # Generación de PDF de rutinas
│   └── workers/               # Tareas async/Celery
│       ├── notifications.py
│       └── webhooks.py
├── tests/
│   ├── conftest.py            # Fixtures (db, client, auth)
│   ├── test_auth.py
│   └── ...
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── .env.example
├── docker-compose.yml         # PostgreSQL + Redis para dev local
├── Dockerfile
└── CLAUDE.md
```

## Roles del sistema (RBAC)

- **super_admin**: CrossDEV internal — gestiona tenants
- **admin**: Administrador/gerente del gimnasio
- **trainer**: Personal trainer / entrenador
- **student**: Cliente / alumno

Permisos se validan SIEMPRE en backend, nunca confiar en frontend.

## Modelo de datos — Entidades principales

- **Tenant**: id, name, slug, plan_type (basic/premium), config, created_at
- **User**: id, tenant_id, email, hashed_password, role, first_name, last_name, phone, is_active, created_at
- **Membership**: id, tenant_id, user_id (student), plan_name, status (active/expired/suspended), start_date, end_date, price
- **TrainerStudentAssignment**: id, tenant_id, trainer_id, student_id, start_date, end_date, status (active/finished) — relación N:N con historial
- **Class**: id, tenant_id, name, trainer_id, schedule, capacity, is_active
- **Booking**: id, tenant_id, class_id, student_id, status (confirmed/cancelled), booked_at
- **Routine**: id, tenant_id, trainer_id, student_id, name, description, created_at
- **RoutineExercise**: id, routine_id, exercise_name, sets, reps, weight, rest_seconds, notes, order
- **Attendance**: id, tenant_id, user_id, class_id (nullable), checked_in_at
- **Conversation**: id, tenant_id, assignment_id, created_at, status
- **ConversationParticipant**: id, conversation_id, user_id, role
- **Message**: id, conversation_id, sender_id, content, message_type (text/image/file), is_read, is_deleted, created_at
- **Attachment**: id, message_id, file_url, file_type, file_size
- **Payment**: id, tenant_id, user_id, membership_id, amount, currency, status (pending/approved/rejected/cancelled), provider (mercadopago), provider_payment_id, created_at
- **Notification**: id, tenant_id, user_id, title, body, type, is_read, created_at
- **AuditLog**: id, tenant_id, user_id, action, resource, resource_id, details (JSON), ip_address, created_at

Todas las tablas con tenant_id tienen foreign key a Tenant. Usar soft delete (is_deleted + deleted_at) en mensajes y usuarios, no DELETE físico.

## Convenciones de código

- Idioma del código: inglés (variables, funciones, clases, comentarios)
- Idioma de la documentación de API: español (descripciones, mensajes de error al usuario)
- Naming: snake_case para variables/funciones, PascalCase para clases/modelos
- Cada router monta en `/api/v1/{dominio}`
- Responses siempre con schema Pydantic explícito
- Errores con HTTPException y formato consistente: `{"detail": "mensaje", "code": "ERROR_CODE"}`
- Paginación: `?page=1&size=20` → response con `items`, `total`, `page`, `size`, `pages`
- Todos los timestamps en UTC, formato ISO 8601
- Variables de entorno en .env, nunca hardcodeadas. Usar Pydantic BaseSettings
- Logging con structlog o loguru, nunca print()

## Comandos

```bash
# Levantar dev
docker-compose up -d                  # PostgreSQL + Redis
uvicorn app.main:app --reload         # Backend

# Migraciones
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Tests
pytest
pytest tests/test_auth.py -v

# Lint
ruff check .
ruff format .
```

## Reglas estrictas

- NUNCA exponer credenciales, tokens o passwords en logs
- NUNCA devolver hashed_password en responses de API
- NUNCA permitir acceso cross-tenant (un gimnasio viendo datos de otro)
- NUNCA conectar frontends directamente a la DB
- Webhook de Mercado Pago es la fuente de verdad para estado de pago
- El chat se persiste ANTES de reenviar por WebSocket
- Adjuntos de chat: validar tipo y tamaño de archivo en backend
- Rate limiting en endpoints de autenticación y endpoints públicos

## Archivos que NO modificar sin instrucción explícita

- alembic.ini (configuración base)
- docker-compose.yml (sin revisión)
- .env.example (actualizar solo cuando se agreguen nuevas variables)

## Contexto del equipo

El equipo mobile (Flutter) y web (React + Vite) trabajan en repos separados.
Los contratos de API que se definan acá son los que ellos van a consumir.
La documentación OpenAPI autogenerada por FastAPI (/docs) es la fuente de verdad de los contratos.
Antes de cambiar un endpoint existente, considerar el impacto en los otros repos.
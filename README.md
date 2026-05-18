# Leads API

API REST para gestión de leads, construida con Python, FastAPI y PostgreSQL.

## Stack tecnológico y decisiones

| Tecnología | Versión | Razón de elección |
|---|---|---|
| **Python 3.12** | 3.12 | Tipado estático maduro, async nativo, ecosistema robusto |
| **FastAPI** | 0.115 | Rendimiento comparable a Node, validación automática con Pydantic, Swagger integrado |
| **PostgreSQL 16** | 16 | ACID, soporte UUID nativo, índices parciales para soft delete |
| **SQLAlchemy 2.0** | 2.0 async | ORM async moderno, type-safe, compatible con Alembic |
| **Alembic** | 1.14 | Migraciones versionadas, reproducibles en cualquier entorno |
| **Anthropic SDK** | 0.40 | Integración con Claude para resúmenes ejecutivos de leads |
| **python-jose** | 3.3 | JWT estándar, bien documentado |
| **slowapi** | 0.1.9 | Rate limiting por IP compatible con FastAPI |
| **pytest-asyncio** | 0.24 | Tests async sin boilerplate |

---

## Prerrequisitos

- Python 3.12+
- PostgreSQL 16+ (o Docker)
- `pip` o `pip3`

---

## Instalación local (sin Docker)

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/leads-api.git
cd leads-api

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Edita .env con tu DATABASE_URL y SECRET_KEY
```

**Crear la base de datos en PostgreSQL:**
```sql
CREATE DATABASE leads_db;
```

```bash
# 5. Ejecutar migraciones
alembic upgrade head

# 6. Ejecutar seed (12 leads de ejemplo)
python seed.py

# 7. Levantar el servidor
uvicorn app.main:app --reload
```

La API estará disponible en: **http://localhost:8000**  
Swagger UI: **http://localhost:8000/docs**

---

## Instalación con Docker (recomendado)

```bash
# Clonar y entrar al proyecto
git clone https://github.com/tu-usuario/leads-api.git
cd leads-api

# Levantar todo (PostgreSQL + API + migraciones + seed)
docker compose up --build
```

La API queda en **http://localhost:8000** con datos de ejemplo listos.

---

## Variables de entorno

Copia `.env.example` a `.env` y ajusta:

| Variable | Requerida | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | URL de conexión async a PostgreSQL |
| `SECRET_KEY` | Sí | Clave para firmar JWT |
| `ANTHROPIC_API_KEY` | No | API key de Anthropic para IA real |
| `AI_MOCK_MODE` | No | `True` = resumen simulado, `False` = IA real |
| `API_KEY` | No | API key estática alternativa a JWT |
| `RATE_LIMIT_PER_MINUTE` | No | Límite de requests por IP (default: 60) |

---

## Autenticación

Todos los endpoints (excepto `POST /auth/token` y `POST /leads/webhook`) requieren un **Bearer JWT**.

```bash
# Obtener token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "onemillion2026"}'

# Respuesta
# {"access_token": "eyJ...", "token_type": "bearer"}
```

Usa el token en el header: `Authorization: Bearer eyJ...`

Credenciales de demo: `admin / onemillion2026` - `demo / demo1234`

---

## Endpoints

### POST /leads - Crear lead
```bash
curl -X POST http://localhost:8000/leads \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "María López",
    "email": "maria@ejemplo.com",
    "telefono": "+57 300 000 0000",
    "fuente": "instagram",
    "producto_interes": "Curso de Marketing",
    "presupuesto": 497
  }'
```

### GET /leads - Listar con filtros y paginación
```bash
# Todos los leads
curl http://localhost:8000/leads \
  -H "Authorization: Bearer TOKEN"

# Con filtros
curl "http://localhost:8000/leads?fuente=instagram&page=1&limit=10" \
  -H "Authorization: Bearer TOKEN"

# Por rango de fechas
curl "http://localhost:8000/leads?fecha_desde=2024-01-01T00:00:00&fecha_hasta=2024-12-31T23:59:59" \
  -H "Authorization: Bearer TOKEN"
```

### GET /leads/stats - Estadísticas
```bash
curl http://localhost:8000/leads/stats \
  -H "Authorization: Bearer TOKEN"
```

### GET /leads/{id} - Obtener lead
```bash
curl http://localhost:8000/leads/UUID-AQUI \
  -H "Authorization: Bearer TOKEN"
```

### PATCH /leads/{id} - Actualizar lead
```bash
curl -X PATCH http://localhost:8000/leads/UUID-AQUI \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"presupuesto": 999, "producto_interes": "Mentoría 1:1"}'
```

### DELETE /leads/{id} - Eliminar (soft delete)
```bash
curl -X DELETE http://localhost:8000/leads/UUID-AQUI \
  -H "Authorization: Bearer TOKEN"
```

### POST /leads/ai/summary - Resumen con IA
```bash
# Sin filtros (todos los leads)
curl -X POST http://localhost:8000/leads/ai/summary \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# Con filtro por fuente
curl -X POST http://localhost:8000/leads/ai/summary \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fuente": "instagram"}'

# Con rango de fechas
curl -X POST http://localhost:8000/leads/ai/summary \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fecha_desde": "2024-01-01T00:00:00Z",
    "fecha_hasta": "2024-12-31T23:59:59Z"
  }'
```

### POST /leads/webhook - Webhook Typeform (sin auth)
```bash
curl -X POST http://localhost:8000/leads/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": "tf_abc123",
    "token": "tok_xyz789",
    "submitted_at": "2024-06-01T10:00:00Z",
    "answers": [
      {"field_id": "nombre", "value": "Carlos Ruiz"},
      {"field_id": "email", "value": "carlos@ejemplo.com"},
      {"field_id": "fuente", "value": "landing_page"},
      {"field_id": "presupuesto", "value": "750"}
    ]
  }'
```

---

## Seed

```bash
# Local
python seed.py

# Docker
docker compose exec api python seed.py
```

Inserta 12 leads distribuidos en los últimos 14 días, con variedad de fuentes y presupuestos.

---

## Tests

```bash
# Instalar dependencias de test (ya incluidas en requirements.txt)
pip install -r requirements.txt

# Ejecutar todos los tests
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --tb=short
```

Los tests usan **SQLite en memoria** - no necesitan PostgreSQL corriendo. Cubren:

- Autenticación (JWT, credenciales incorrectas, endpoint sin token)
- Creación de leads (éxito, email duplicado, email inválido, fuente inválida, nombre muy corto)
- Listado con paginación y filtros
- Obtener lead por ID (éxito y 404)
- Actualización (éxito y conflicto de email)
- Soft delete
- Estadísticas
- Webhook Typeform

---

## Integración con IA

La arquitectura está preparada para dos modos:

**Modo mock** (default, sin costo):
```env
AI_MOCK_MODE=True
```
Retorna un resumen estructurado generado localmente con los datos reales de los leads.

**Modo real** (Claude de Anthropic):
```env
ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui
AI_MOCK_MODE=False
```
El campo `mock: true/false` en la respuesta indica qué modo se usó.

La lógica de IA está aislada en `app/services/ai_service.py`, facilitando cambiar de proveedor (OpenAI, Gemini, etc.) sin tocar los endpoints.

---

## Estructura del proyecto

```
leads-api/
├── app/
│   ├── api/routes/
│   │   ├── auth.py          # POST /auth/token
│   │   └── leads.py         # Todos los endpoints /leads
│   ├── core/
│   │   ├── config.py        # Settings desde .env
│   │   └── security.py      # JWT + API Key
│   ├── db/
│   │   └── database.py      # Engine async + session
│   ├── models/
│   │   └── lead.py          # SQLAlchemy ORM model
│   ├── schemas/
│   │   └── lead.py          # Pydantic schemas (in/out)
│   ├── services/
│   │   ├── lead_service.py  # Lógica de negocio
│   │   └── ai_service.py    # Integración LLM
│   └── main.py              # App FastAPI + middleware
├── alembic/                 # Migraciones
├── tests/
│   └── test_leads.py        # 20+ tests
├── seed.py                  # Datos de ejemplo
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Decisiones de diseño

- **Soft delete**: Los leads eliminados tienen `is_deleted=true` y `deleted_at` con timestamp. No se listan ni se pueden consultar por ID, pero los datos se conservan para auditoría.
- **UUID como PK**: Evita enumeración de recursos y es más seguro que IDs secuenciales.
- **Fuentes como Enum**: Validación estricta de los valores permitidos, extensible sin migraciones.
- **Email lowercase**: Normalizado en ingesta para evitar duplicados por capitalización.
- **Paginación por defecto**: Todos los listados están paginados para proteger el rendimiento.
- **GET /leads/stats antes de GET /leads/:id**: El orden de rutas en FastAPI importa - la ruta literal `/stats` debe registrarse antes del parámetro dinámico `/{lead_id}`.

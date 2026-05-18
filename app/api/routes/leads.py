import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.schemas.lead import (
    AISummaryRequest,
    AISummaryResponse,
    LeadCreate,
    LeadResponse,
    LeadsStats,
    LeadUpdate,
    PaginatedLeads,
    TypeformWebhookPayload,
)
from app.services.ai_service import generate_leads_summary
from app.services.lead_service import lead_service

router = APIRouter(prefix="/leads", tags=["Leads"])


# POST /leads

@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo lead",
)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return await lead_service.create_lead(db, data)


# GET /leads/stats  (must be before /:id to avoid routing conflict)

@router.get(
    "/stats",
    response_model=LeadsStats,
    summary="Estadísticas generales de leads",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return await lead_service.get_stats(db)


# POST /leads/ai/summary

@router.post(
    "/ai/summary",
    response_model=AISummaryResponse,
    summary="Resumen ejecutivo con IA",
    description=(
        "Filtra leads y genera un análisis ejecutivo usando Claude (Anthropic). "
        "Si `AI_MOCK_MODE=True` o no hay API key, retorna una simulación documentada."
    ),
)
async def ai_summary(
    filters: AISummaryRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    leads = await lead_service.get_leads_for_ai(
        db,
        fuente=filters.fuente.value if filters.fuente else None,
        fecha_desde=filters.fecha_desde,
        fecha_hasta=filters.fecha_hasta,
    )

    applied_filters = filters.model_dump(exclude_none=True)
    summary, is_mock = await generate_leads_summary(leads, applied_filters)

    return AISummaryResponse(
        resumen=summary,
        leads_analizados=len(leads),
        filtros_aplicados=applied_filters,
        generado_en=datetime.utcnow(),
        mock=is_mock,
    )


# POST /leads/webhook

@router.post(
    "/webhook",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Webhook estilo Typeform",
    description=(
        "Simula un webhook de Typeform. Mapea las respuestas del formulario "
        "a campos de Lead y registra el prospecto automáticamente.\n\n"
        "**Campos esperados (field_id):** `nombre`, `email`, `telefono`, "
        "`fuente`, `producto_interes`, `presupuesto`."
    ),
)
async def typeform_webhook(
    payload: TypeformWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    No requiere autenticación JWT — el caller es el servidor de Typeform.
    En producción se validaría la firma HMAC del header X-Typeform-Signature.
    """
    field_map: dict[str, str] = {}
    for answer in payload.answers:
        field_map[answer.field_id] = str(answer.value)

    from app.schemas.lead import FuenteEnum

    fuente_raw = field_map.get("fuente", "otro")
    try:
        fuente = FuenteEnum(fuente_raw)
    except ValueError:
        fuente = FuenteEnum.otro

    lead_data = LeadCreate(
        nombre=field_map.get("nombre", "Sin nombre"),
        email=field_map.get("email", f"noemail_{payload.token}@webhook.invalid"),
        telefono=field_map.get("telefono"),
        fuente=fuente,
        producto_interes=field_map.get("producto_interes"),
        presupuesto=float(field_map["presupuesto"]) if "presupuesto" in field_map else None,
    )
    return await lead_service.create_lead(db, lead_data)


# GET /leads

@router.get(
    "",
    response_model=PaginatedLeads,
    summary="Listar leads con paginación y filtros",
)
async def list_leads(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Resultados por página"),
    fuente: Optional[str] = Query(None, description="Filtrar por fuente"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha de fin (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return await lead_service.list_leads(
        db,
        page=page,
        limit=limit,
        fuente=fuente,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


# GET /leads/:id

@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Obtener un lead por ID",
)
async def get_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return await lead_service.get_lead(db, lead_id)


# PATCH /leads/:id

@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Actualizar un lead existente",
)
async def update_lead(
    lead_id: uuid.UUID,
    data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return await lead_service.update_lead(db, lead_id, data)


# DELETE /leads/:id

@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un lead (soft delete)",
)
async def delete_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    await lead_service.delete_lead(db, lead_id)

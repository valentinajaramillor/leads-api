import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate


class LeadService:

    # Create

    async def create_lead(self, db: AsyncSession, data: LeadCreate) -> Lead:
        existing = await db.scalar(
            select(Lead).where(Lead.email == data.email, Lead.is_deleted.is_(False))
        )
        if existing:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un lead con el email '{data.email}'",
            )

        lead = Lead(**data.model_dump())
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead

    # List

    async def list_leads(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        fuente: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> dict:
        base_query = select(Lead).where(Lead.is_deleted.is_(False))

        if fuente:
            base_query = base_query.where(Lead.fuente == fuente)
        if fecha_desde:
            base_query = base_query.where(Lead.created_at >= fecha_desde)
        if fecha_hasta:
            base_query = base_query.where(Lead.created_at <= fecha_hasta)

        # Total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await db.scalar(count_query) or 0

        # Paginated results - most recent first
        results = await db.scalars(
            base_query.order_by(Lead.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        leads = list(results.all())

        return {
            "data": leads,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total else 0,
        }

    # Get by ID

    async def get_lead(self, db: AsyncSession, lead_id: uuid.UUID) -> Lead:
        lead = await db.scalar(
            select(Lead).where(Lead.id == lead_id, Lead.is_deleted.is_(False))
        )
        if not lead:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead con id '{lead_id}' no encontrado",
            )
        return lead

    # Update

    async def update_lead(
        self, db: AsyncSession, lead_id: uuid.UUID, data: LeadUpdate
    ) -> Lead:
        lead = await self.get_lead(db, lead_id)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron campos para actualizar",
            )

        # Check unique email if email is being changed
        if "email" in update_data and update_data["email"] != lead.email:
            existing = await db.scalar(
                select(Lead).where(
                    Lead.email == update_data["email"],
                    Lead.is_deleted.is_(False),
                    Lead.id != lead_id,
                )
            )
            if existing:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe un lead con el email '{update_data['email']}'",
                )

        for field, value in update_data.items():
            setattr(lead, field, value)

        lead.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(lead)
        return lead

    # Soft Delete

    async def delete_lead(self, db: AsyncSession, lead_id: uuid.UUID) -> None:
        lead = await self.get_lead(db, lead_id)
        lead.is_deleted = True
        lead.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    # Stats

    async def get_stats(self, db: AsyncSession) -> dict:
        active = Lead.is_deleted.is_(False)

        total = await db.scalar(select(func.count(Lead.id)).where(active)) or 0

        # Leads per source
        rows = await db.execute(
            select(Lead.fuente, func.count(Lead.id).label("cantidad"))
            .where(active)
            .group_by(Lead.fuente)
            .order_by(func.count(Lead.id).desc())
        )
        leads_por_fuente = [
            {"fuente": row.fuente, "cantidad": row.cantidad} for row in rows
        ]

        avg_budget = await db.scalar(
            select(func.avg(Lead.presupuesto)).where(active, Lead.presupuesto.isnot(None))
        )

        since_7_days = datetime.now(timezone.utc) - timedelta(days=7)
        last_7 = await db.scalar(
            select(func.count(Lead.id)).where(active, Lead.created_at >= since_7_days)
        ) or 0

        return {
            "total_leads": total,
            "leads_por_fuente": leads_por_fuente,
            "promedio_presupuesto": round(float(avg_budget), 2) if avg_budget else None,
            "leads_ultimos_7_dias": last_7,
        }

    # Filtered leads for AI

    async def get_leads_for_ai(
        self,
        db: AsyncSession,
        fuente: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> list[Lead]:
        query = select(Lead).where(Lead.is_deleted.is_(False))

        if fuente:
            query = query.where(Lead.fuente == fuente)
        if fecha_desde:
            query = query.where(Lead.created_at >= fecha_desde)
        if fecha_hasta:
            query = query.where(Lead.created_at <= fecha_hasta)

        results = await db.scalars(query.order_by(Lead.created_at.desc()))
        return list(results.all())


lead_service = LeadService()

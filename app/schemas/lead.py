import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class FuenteEnum(str, Enum):
    instagram = "instagram"
    facebook = "facebook"
    landing_page = "landing_page"
    referido = "referido"
    otro = "otro"


# Request schemas

class LeadCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=255, description="Nombre completo del lead")
    email: EmailStr = Field(..., description="Correo electrónico único")
    telefono: Optional[str] = Field(None, max_length=50, description="Teléfono de contacto")
    fuente: FuenteEnum = Field(..., description="Canal de origen del lead")
    producto_interes: Optional[str] = Field(None, max_length=255, description="Producto de interés")
    presupuesto: Optional[float] = Field(None, ge=0, description="Presupuesto en USD")

    @field_validator("nombre")
    @classmethod
    def nombre_no_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class LeadUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=50)
    fuente: Optional[FuenteEnum] = None
    producto_interes: Optional[str] = Field(None, max_length=255)
    presupuesto: Optional[float] = Field(None, ge=0)

    @field_validator("nombre")
    @classmethod
    def nombre_no_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip() if v else v

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else v


# Response schemas

class LeadResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    email: str
    telefono: Optional[str]
    fuente: FuenteEnum
    producto_interes: Optional[str]
    presupuesto: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedLeads(BaseModel):
    data: list[LeadResponse]
    total: int
    page: int
    limit: int
    pages: int


# Stats schema

class LeadsBySource(BaseModel):
    fuente: str
    cantidad: int


class LeadsStats(BaseModel):
    total_leads: int
    leads_por_fuente: list[LeadsBySource]
    promedio_presupuesto: Optional[float]
    leads_ultimos_7_dias: int


# AI schema

class AISummaryRequest(BaseModel):
    fuente: Optional[FuenteEnum] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None


class AISummaryResponse(BaseModel):
    resumen: str
    leads_analizados: int
    filtros_aplicados: dict
    generado_en: datetime
    mock: bool = Field(
        False,
        description="True cuando la respuesta es simulada (sin API key real configurada)"
    )


# Auth schema

class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Webhook schema

class TypeformAnswer(BaseModel):
    field_id: str
    value: str | float


class TypeformWebhookPayload(BaseModel):
    """Simulates a Typeform webhook payload structure."""
    form_id: str
    token: str
    submitted_at: datetime
    answers: list[TypeformAnswer]

"""
AI Service - integración con Anthropic Claude.

Comportamiento:
- Si ANTHROPIC_API_KEY está configurado y AI_MOCK_MODE=False -> llama a la API real
- En cualquier otro caso -> retorna un resumen simulado bien estructurado (mock=True)

Para activar la integración real sólo es necesario:
  1. Poner la API key en .env  ->  ANTHROPIC_API_KEY=sk-ant-...
  2. Poner  AI_MOCK_MODE=False  en .env
"""

import json
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.models.lead import Lead


def _leads_to_summary_payload(leads: list[Lead]) -> list[dict]:
    """Convierte los modelos ORM a dicts simples para el prompt."""
    return [
        {
            "nombre": l.nombre,
            "email": l.email,
            "fuente": l.fuente,
            "producto_interes": l.producto_interes,
            "presupuesto": l.presupuesto,
            "created_at": l.created_at.isoformat(),
        }
        for l in leads
    ]


def _build_prompt(leads_data: list[dict], filters: dict) -> str:
    filters_str = json.dumps(filters, ensure_ascii=False, default=str)
    leads_str = json.dumps(leads_data, ensure_ascii=False, indent=2)

    return f"""Eres un analista de marketing digital especializado en embudos de venta.
Se te entrega una lista de leads (prospectos) de One Million Copy SAS,
una empresa que ayuda a creadores digitales a vender sus productos en internet.

Filtros aplicados: {filters_str}
Total de leads: {len(leads_data)}

Datos de los leads:
{leads_str}

Genera un resumen ejecutivo en español que incluya:
1. **Análisis general**: Descripción del estado actual de los leads.
2. **Fuente principal**: Canal que más leads genera y por qué es relevante.
3. **Perfil de presupuesto**: Análisis del rango de presupuesto de los prospectos.
4. **Recomendaciones**: Al menos 3 acciones concretas para optimizar la captación.
5. **Próximos pasos**: Qué hacer con estos leads en las próximas 48 horas.

Sé conciso, directo y accionable. Usa viñetas cuando ayude a la legibilidad."""


async def _call_anthropic(prompt: str) -> str:
    """Llama a la API real de Anthropic."""
    import anthropic  # type: ignore

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _mock_summary(leads_data: list[dict], filters: dict) -> str:
    """
    Resumen simulado — representativo de lo que devolvería el LLM real.
    Documentado explícitamente como mock para evaluación.
    """
    total = len(leads_data)
    if total == 0:
        return (
            "**Análisis general:** No se encontraron leads con los filtros aplicados.\n\n"
            "**Recomendaciones:**\n"
            "- Amplía el rango de fechas del filtro.\n"
            "- Verifica que los canales estén activos.\n"
            "- Considera lanzar una nueva campaña de captación."
        )

    fuentes: dict[str, int] = {}
    presupuestos = []
    for lead in leads_data:
        fuentes[lead["fuente"]] = fuentes.get(lead["fuente"], 0) + 1
        if lead["presupuesto"]:
            presupuestos.append(lead["presupuesto"])

    top_fuente = max(fuentes, key=fuentes.__getitem__)
    avg_budget = round(sum(presupuestos) / len(presupuestos), 2) if presupuestos else None
    budget_str = f"USD {avg_budget}" if avg_budget else "no disponible"

    fuentes_list = "\n".join(
        f"  - {f}: {c} lead{'s' if c > 1 else ''}" for f, c in sorted(fuentes.items(), key=lambda x: -x[1])
    )

    return f"""**Análisis general** *(resumen simulado — activa ANTHROPIC_API_KEY para IA real)*

Se analizaron **{total} leads** captados a través de {len(fuentes)} canal(es) de marketing.
El pipeline muestra actividad en todas las fuentes configuradas.

**Fuente principal:** `{top_fuente}` lidera con **{fuentes[top_fuente]} leads** ({round(fuentes[top_fuente]/total*100)}% del total).
Esto indica que las campañas en este canal están funcionando bien y merecen mayor inversión.

**Distribución por fuente:**
{fuentes_list}

**Perfil de presupuesto:**
El presupuesto promedio declarado es **{budget_str}**, lo que permite estimar el ticket potencial
del segmento y ajustar la propuesta de valor.

**Recomendaciones:**
1. **Potenciar `{top_fuente}`:** Aumentar el gasto/esfuerzo en este canal dado el volumen generado.
2. **Nutrir leads sin presupuesto declarado:** Crear una secuencia de email que ayude a calificarlos financieramente.
3. **Activar retargeting en fuentes secundarias:** Los canales con menos volumen pueden mejorar con creatividades específicas.
4. **Segmentar por producto de interés:** Personalizar el seguimiento según el producto mencionado aumenta la tasa de conversión.

**Próximos pasos (48 h):**
- Contactar por WhatsApp a los leads de las últimas 24 h.
- Enviar caso de éxito relevante a leads con presupuesto ≥ USD 500.
- Revisar leads sin teléfono y activar secuencia de email de calificación.
"""


async def generate_leads_summary(
    leads: list[Lead],
    filters: dict,
) -> tuple[str, bool]:
    """
    Retorna (resumen: str, es_mock: bool).
    Intenta la API real; si falla o no está configurada, usa el mock.
    """
    leads_data = _leads_to_summary_payload(leads)
    prompt = _build_prompt(leads_data, filters)

    use_real_api = (
        settings.ANTHROPIC_API_KEY
        and settings.ANTHROPIC_API_KEY.startswith("sk-ant-")
        and not settings.AI_MOCK_MODE
    )

    if use_real_api:
        try:
            summary = await _call_anthropic(prompt)
            return summary, False
        except Exception as exc:
            # Fallback to mock on any API error — log in production
            print(f"[AI Service] Error llamando Anthropic API: {exc}. Usando mock.")

    return _mock_summary(leads_data, filters), True

"""
Seed script - inserta 12 leads de ejemplo en la base de datos.

Uso:
    python seed.py

Requiere que DATABASE_URL esté configurado en .env o como variable de entorno.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

# Allow running from project root
sys.path.insert(0, ".")

from app.db.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.models.lead import Lead  # noqa: E402

SEED_LEADS = [
    {
        "nombre": "Valentina Torres",
        "email": "valentina.torres@gmail.com",
        "telefono": "+57 300 123 4567",
        "fuente": "instagram",
        "producto_interes": "Curso de Marketing Digital",
        "presupuesto": 497.0,
    },
    {
        "nombre": "Andrés Mejía",
        "email": "andres.mejia@hotmail.com",
        "telefono": "+57 315 987 6543",
        "fuente": "facebook",
        "producto_interes": "Mentoría 1:1",
        "presupuesto": 1200.0,
    },
    {
        "nombre": "Camila Rodríguez",
        "email": "camila.rodriguez@empresa.co",
        "telefono": None,
        "fuente": "landing_page",
        "producto_interes": "Plantillas de Contenido",
        "presupuesto": 97.0,
    },
    {
        "nombre": "Felipe Gómez",
        "email": "felipe.gomez@outlook.com",
        "telefono": "+57 320 456 7890",
        "fuente": "referido",
        "producto_interes": "Curso de Marketing Digital",
        "presupuesto": 497.0,
    },
    {
        "nombre": "Laura Sánchez",
        "email": "laura.sanchez@gmail.com",
        "telefono": "+57 311 234 5678",
        "fuente": "instagram",
        "producto_interes": "Mentoría Grupal",
        "presupuesto": 297.0,
    },
    {
        "nombre": "Diego Martínez",
        "email": "diego.martinez@yahoo.com",
        "telefono": None,
        "fuente": "facebook",
        "producto_interes": None,
        "presupuesto": None,
    },
    {
        "nombre": "Sofía Vargas",
        "email": "sofia.vargas@gmail.com",
        "telefono": "+57 304 567 8901",
        "fuente": "landing_page",
        "producto_interes": "Curso de Ventas Online",
        "presupuesto": 750.0,
    },
    {
        "nombre": "Mateo Herrera",
        "email": "mateo.herrera@empresa.co",
        "telefono": "+57 318 901 2345",
        "fuente": "instagram",
        "producto_interes": "Plantillas de Contenido",
        "presupuesto": 97.0,
    },
    {
        "nombre": "Isabela Castro",
        "email": "isabela.castro@gmail.com",
        "telefono": None,
        "fuente": "referido",
        "producto_interes": "Mentoría 1:1",
        "presupuesto": 1500.0,
    },
    {
        "nombre": "Sebastián López",
        "email": "sebastian.lopez@hotmail.com",
        "telefono": "+57 322 678 9012",
        "fuente": "otro",
        "producto_interes": "Curso de Marketing Digital",
        "presupuesto": 497.0,
    },
    {
        "nombre": "Mariana Peña",
        "email": "mariana.pena@gmail.com",
        "telefono": "+57 313 345 6789",
        "fuente": "instagram",
        "producto_interes": "Mentoría Grupal",
        "presupuesto": 297.0,
    },
    {
        "nombre": "Julián Moreno",
        "email": "julian.moreno@empresa.co",
        "telefono": None,
        "fuente": "facebook",
        "producto_interes": "Curso de Ventas Online",
        "presupuesto": 350.0,
    },
]


async def seed():
    # Create tables if needed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check for existing seeds to avoid duplicates
        existing_emails = {
            row[0]
            for row in (
                await session.execute(
                    text("SELECT email FROM leads WHERE is_deleted = false")
                )
            ).fetchall()
        }

        new_leads = []
        now = datetime.now(timezone.utc)

        for i, data in enumerate(SEED_LEADS):
            if data["email"] in existing_emails:
                print(f"  -  Skipping (already exists): {data['email']}")
                continue

            # Spread created_at over the last 14 days for realistic stats
            days_ago = (len(SEED_LEADS) - i) % 14
            created = now - timedelta(days=days_ago, hours=i * 2)

            lead = Lead(**data, created_at=created, updated_at=created)
            session.add(lead)
            new_leads.append(data["email"])

        await session.commit()

        if new_leads:
            print(f"\nSeed completado - {len(new_leads)} leads insertados:")
            for email in new_leads:
                print(f"   - {email}")
        else:
            print("\nTodos los leads del seed ya existían. No se insertó nada.")


if __name__ == "__main__":
    print("Ejecutando seed...")
    asyncio.run(seed())

from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.schemas.lead import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

# Demo credentials - in production these would be validated against a users table.
DEMO_USERS = {
    "admin": "onemillion2026",
    "demo": "demo1234",
}


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtener token JWT",
    description=(
        "Genera un token de acceso JWT. Credenciales de demo:\n\n"
        "- `admin` / `onemillion2026`\n"
        "- `demo` / `demo1234`"
    ),
)
async def login(data: TokenRequest):
    expected_password = DEMO_USERS.get(data.username)
    if not expected_password or expected_password != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    token = create_access_token({"sub": data.username})
    return TokenResponse(access_token=token)

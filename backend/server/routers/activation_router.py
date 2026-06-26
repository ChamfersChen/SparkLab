from fastapi import APIRouter, Depends
from sparklab.schemas.auth import (
    ActivateRequest,
    ActivateResponse,
    ActivationVerifyRequest,
    ActivationVerifyResponse,
)
from sparklab.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db

activation = APIRouter(prefix="/activation", tags=["激活"])


@activation.post("/verify", response_model=ActivationVerifyResponse)
async def verify_code(
    body: ActivationVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    valid, message = await service.verify_activation_code(body.code)
    return ActivationVerifyResponse(valid=valid, message=message)


@activation.post("/activate", response_model=ActivateResponse)
async def activate(
    body: ActivateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.activate(body.code, body.username, body.password)

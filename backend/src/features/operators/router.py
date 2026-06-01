"""HTTP API присутствия операторов."""

from fastapi import APIRouter, Depends

from src.core.security import CurrentOperator, get_current_operator
from src.features.operators.schemas import (
    OperatorMeResponse,
    OperatorStatusRequest,
    OperatorStatusResponse,
)
from src.features.operators.service import OperatorService, get_operator_service

router = APIRouter(prefix='/operators', tags=['Операторы'])


@router.post('/status', response_model=OperatorStatusResponse)
async def set_operator_status(
    payload: OperatorStatusRequest,
    current: CurrentOperator = Depends(get_current_operator),
    service: OperatorService = Depends(get_operator_service),
) -> OperatorStatusResponse:
    """Переключает статус текущего оператора (онлайн/офлайн)."""
    return await service.set_status(operator_id=current.id, online=payload.online)


@router.get('/me', response_model=OperatorMeResponse)
async def get_me(
    current: CurrentOperator = Depends(get_current_operator),
    service: OperatorService = Depends(get_operator_service),
) -> OperatorMeResponse:
    """Возвращает статус и нагрузку текущего оператора."""
    return await service.get_me(operator_id=current.id)

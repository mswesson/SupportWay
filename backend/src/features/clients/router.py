"""HTTP API клиентов (CRUD)."""

from fastapi import APIRouter, Depends, Query, status

from src.features.clients.schemas import (
    ClientCreateRequest,
    ClientCreateResponse,
    ClientGetResponse,
    ClientListResponse,
    ClientUpdateRequest,
    ClientUpdateResponse,
)
from src.features.clients.service import ClientService, get_client_service

router = APIRouter(prefix='/clients', tags=['Клиенты'])


@router.post('/', response_model=ClientCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreateRequest,
    service: ClientService = Depends(get_client_service),
) -> ClientCreateResponse:
    """Создаёт клиента."""
    return await service.create(payload)


@router.get('/', response_model=ClientListResponse)
async def list_clients(
    page: int = Query(1, ge=1, description='Номер страницы'),
    page_size: int = Query(50, ge=1, le=500, description='Записей на странице'),
    service: ClientService = Depends(get_client_service),
) -> ClientListResponse:
    """Возвращает постраничный список клиентов."""
    return await service.get_list(page=page, page_size=page_size)


@router.get('/{client_id}', response_model=ClientGetResponse)
async def get_client(
    client_id: int,
    service: ClientService = Depends(get_client_service),
) -> ClientGetResponse:
    """Возвращает клиента по id."""
    return await service.get_one(client_id)


@router.put('/{client_id}', response_model=ClientUpdateResponse)
async def update_client(
    client_id: int,
    payload: ClientUpdateRequest,
    service: ClientService = Depends(get_client_service),
) -> ClientUpdateResponse:
    """Обновляет клиента."""
    return await service.update(client_id, payload)


@router.delete('/{client_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    service: ClientService = Depends(get_client_service),
) -> None:
    """Удаляет клиента."""
    await service.delete(client_id)

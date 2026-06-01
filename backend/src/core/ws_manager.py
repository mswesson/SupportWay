"""Менеджер WebSocket-соединений с рассылкой эвентов между воркерами через Redis Pub/Sub.

Каждый воркер держит свои соединения в памяти. Чтобы доставить эвент адресату, чей сокет
может находиться на другом воркере, эвент публикуется в общий Redis-канал. Все воркеры
подписаны на него; доставляет тот, у кого есть нужное соединение.
"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from loguru import logger
from redis.asyncio import Redis

from src.core.config import settings


class ConnectionManager:
    """Хранит локальные WebSocket-соединения и рассылает эвенты через Redis Pub/Sub."""

    def __init__(self) -> None:
        # Соединения, открытые именно на этом воркере.
        self._operators: dict[int, WebSocket] = {}
        self._chats: dict[int, list[WebSocket]] = {}
        self._redis: Redis | None = None
        self._listener_task: asyncio.Task[None] | None = None

    # --- Регистрация локальных соединений ---

    async def connect_operator(self, operator_id: int, websocket: WebSocket) -> None:
        """Принимает и сохраняет соединение оператора."""
        await websocket.accept()
        self._operators[operator_id] = websocket

    def disconnect_operator(self, operator_id: int) -> None:
        """Удаляет соединение оператора."""
        self._operators.pop(operator_id, None)

    async def connect_client(self, chat_id: int, websocket: WebSocket) -> None:
        """Принимает и сохраняет соединение клиентской стороны по чату."""
        await websocket.accept()
        self._chats.setdefault(chat_id, []).append(websocket)

    def disconnect_client(self, chat_id: int, websocket: WebSocket) -> None:
        """Удаляет соединение клиентской стороны."""
        connections = self._chats.get(chat_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self._chats.pop(chat_id, None)

    # --- Публикация эвентов (уходит на все воркеры) ---

    async def send_to_operator(
        self, operator_id: int, event_type: str, data: dict[str, Any]
    ) -> None:
        """Публикует эвент для конкретного оператора."""
        await self._publish(
            {'target': 'operator', 'operator_id': operator_id, 'type': event_type, 'data': data}
        )

    async def send_to_chat(self, chat_id: int, event_type: str, data: dict[str, Any]) -> None:
        """Публикует эвент для всех соединений клиентской стороны чата."""
        await self._publish(
            {'target': 'chat', 'chat_id': chat_id, 'type': event_type, 'data': data}
        )

    async def _publish(self, event: dict[str, Any]) -> None:
        if self._redis is None:
            raise RuntimeError('ConnectionManager не запущен (нет Redis)')
        await self._redis.publish(settings.WS_EVENTS_CHANNEL, json.dumps(event))

    # --- Фоновый слушатель Pub/Sub ---

    async def start(self, redis: Redis) -> None:
        """Запускает фоновую подписку на канал эвентов. Вызывается в lifespan."""
        self._redis = redis
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        """Останавливает фоновую подписку."""
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

    async def _listen(self) -> None:
        """Слушает канал Redis и доставляет эвенты локальным соединениям.

        Используется опрос get_message с таймаутом: при простое он возвращает None
        (без исключений), поэтому фоновый слушатель работает спокойно. Переподписка
        происходит только при реальном обрыве соединения.
        """
        assert self._redis is not None
        while True:
            pubsub = self._redis.pubsub()
            try:
                await pubsub.subscribe(settings.WS_EVENTS_CHANNEL)
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message is None or message.get('type') != 'message':
                        continue
                    try:
                        event = json.loads(message['data'])
                        await self._deliver_local(event)
                    except Exception:
                        logger.exception('Ошибка доставки WS-эвента')
            except asyncio.CancelledError:
                await pubsub.aclose()
                raise
            except Exception:
                # Реальный обрыв соединения — переподписываемся и продолжаем.
                logger.warning('WS-слушатель Redis переподключается')
                await pubsub.aclose()
                await asyncio.sleep(1)

    async def _deliver_local(self, event: dict[str, Any]) -> None:
        """Доставляет эвент соединениям, открытым на этом воркере."""
        payload = {'type': event['type'], **event.get('data', {})}
        if event['target'] == 'operator':
            websocket = self._operators.get(event['operator_id'])
            if websocket is not None:
                await self._safe_send(websocket, payload)
        elif event['target'] == 'chat':
            for websocket in list(self._chats.get(event['chat_id'], [])):
                await self._safe_send(websocket, payload)

    async def _safe_send(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            logger.warning('Не удалось отправить в WebSocket — соединение закрыто')


# Один менеджер на весь процесс.
ws_manager = ConnectionManager()

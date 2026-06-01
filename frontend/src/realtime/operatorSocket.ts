// WebSocket оператора: подключение с JWT, реконнект с backoff, доставка событий.

import { wsUrl } from '../api/http';
import { ChatMessage, SenderRole } from '../types';

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

interface AssignedClient {
  full_name: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  external_id: string | null;
}

export interface OperatorSocketHandlers {
  onStatusChange: (status: ConnectionStatus) => void;
  onChatAssigned: (chatId: number, client: AssignedClient) => void;
  onNewMessage: (message: ChatMessage) => void;
  onSessionClosed: (chatId: number) => void;
  // Вызывается после успешного переподключения — повод досинхронизировать историю.
  onReconnected: () => void;
}

/** Переводит строковый sender из WS-события в роль UI (client -> customer). */
function wsSenderToRole(sender: string): SenderRole {
  if (sender === 'operator') return 'operator';
  if (sender === 'client') return 'customer';
  return 'system';
}

const MAX_RECONNECT_DELAY = 32; // секунды

/** Управляет одним WebSocket-соединением оператора. */
export class OperatorSocket {
  private ws: WebSocket | null = null;
  private reconnectDelay = 1; // секунды
  private reconnectTimer: number | null = null;
  private manualClose = false;
  private hadConnection = false; // была ли уже успешная сессия

  constructor(
    private readonly token: string,
    private readonly handlers: OperatorSocketHandlers,
  ) {}

  /** Открывает соединение (и переоткрывает при реконнекте). */
  connect(): void {
    this.manualClose = false;
    const ws = new WebSocket(wsUrl(`/ws/operator?token=${encodeURIComponent(this.token)}`));
    this.ws = ws;

    ws.onopen = () => {
      this.reconnectDelay = 1;
      this.handlers.onStatusChange('connected');
      if (this.hadConnection) {
        this.handlers.onReconnected();
      }
      this.hadConnection = true;
    };

    ws.onmessage = (event) => {
      let data: any;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      switch (data.type) {
        case 'chat_assigned':
          this.handlers.onChatAssigned(data.chat_id, data.client);
          break;
        case 'new_message':
          this.handlers.onNewMessage({
            id: data.message_id,
            chatId: data.chat_id,
            sender: wsSenderToRole(data.sender),
            text: data.text,
            createdAt: data.created_at,
          });
          break;
        case 'session_closed':
          this.handlers.onSessionClosed(data.chat_id);
          break;
        // ping/error и прочее — игнорируем
        default:
          break;
      }
    };

    ws.onclose = () => {
      if (this.manualClose) {
        this.handlers.onStatusChange('disconnected');
        return;
      }
      this.handlers.onStatusChange('reconnecting');
      this.scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY);
      this.connect();
    }, this.reconnectDelay * 1000);
  }

  /** Отправляет сообщение оператора в чат (ответ придёт обратно эхом new_message). */
  sendMessage(chatId: number, text: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'new_message', chat_id: chatId, text }));
    }
  }

  /** Закрывает соединение без реконнекта (logout/unmount). */
  close(): void {
    this.manualClose = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }
}

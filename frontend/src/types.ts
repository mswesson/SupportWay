// Статусы чата в терминах бэкенда (нижний регистр).
export type ChatStatus = 'pending' | 'reserved' | 'active' | 'closed';

// Тип отправителя в UI: customer — это client на бэкенде.
export type SenderRole = 'operator' | 'customer' | 'system';

export interface ChatMessage {
  id: number;
  chatId: number;
  sender: SenderRole;
  text: string;
  createdAt: string; // ISO 8601, форматируется в HH:MM при выводе
}

export interface ChatSession {
  id: number;
  customerName: string;
  customerPhone: string | null;
  customerEmail: string | null;
  source: string | null; // проект-источник (например TelegramBot)
  externalId: string | null; // ID клиента в системе-источнике
  status: ChatStatus;
  operatorId: number | null;
  createdAt: string;
  acceptedAt: string | null;
  closedAt: string | null;
  messages: ChatMessage[];
  rating: number | null;
}

export interface Operator {
  id: number;
  fullName: string;
  status: 'online' | 'offline';
  activeChatsCount: number;
}

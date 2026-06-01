// Работа с чатами оператора: список, история, действия + мапперы бэкенд -> UI.

import { apiFetch } from './http';
import { ChatSession, ChatMessage, ChatStatus, SenderRole } from '../types';

// --- DTO бэкенда ---

interface ClientInfo {
  full_name: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  external_id: string | null;
}

interface MyChatItem {
  chat_id: number;
  status: string;
  client: ClientInfo;
  created_at: string;
  accepted_at: string | null;
}

interface MyChatsResponse {
  items: MyChatItem[];
}

interface ClosedChatItem {
  chat_id: number;
  status: string;
  client: ClientInfo;
  created_at: string;
  closed_at: string | null;
  rating: number | null;
}

interface ClosedChatsResponse {
  items: ClosedChatItem[];
  total: number;
  page: number;
  page_size: number;
}

/** Страница чатов: элементы + метаданные пагинации. */
export interface PagedChats {
  items: ChatSession[];
  total: number;
  page: number;
  pageSize: number;
}

export const PAGE_SIZE = 10;

interface HistoryMessageItem {
  id: number;
  sender_type_id: number;
  sender_id: number | null;
  text: string;
  created_at: string;
}

interface HistoryResponse {
  chat_id: number;
  items: HistoryMessageItem[];
}

/** Форматирует ISO-время в HH:MM для отображения. */
export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

/** Маппинг элемента /chats/my -> ChatSession (без сообщений). */
function mapChat(item: MyChatItem, operatorId: number | null): ChatSession {
  return {
    id: item.chat_id,
    customerName: item.client.full_name ?? '',
    customerPhone: item.client.phone,
    customerEmail: item.client.email,
    source: item.client.source,
    externalId: item.client.external_id,
    status: item.status as ChatStatus,
    operatorId,
    createdAt: item.created_at,
    acceptedAt: item.accepted_at,
    closedAt: null,
    messages: [],
    rating: null,
  };
}

/** Маппинг элемента /chats/closed -> ChatSession (без сообщений). */
function mapClosedChat(item: ClosedChatItem, operatorId: number | null): ChatSession {
  return {
    id: item.chat_id,
    customerName: item.client.full_name ?? '',
    customerPhone: item.client.phone,
    customerEmail: item.client.email,
    source: item.client.source,
    externalId: item.client.external_id,
    status: 'closed',
    operatorId,
    createdAt: item.created_at,
    acceptedAt: null,
    closedAt: item.closed_at,
    messages: [],
    rating: item.rating,
  };
}

/** Строит ChatSession из события chat_assigned (новый зарезервированный чат). */
export function mapAssignedChat(
  chatId: number,
  client: ClientInfo,
  operatorId: number | null,
): ChatSession {
  return {
    id: chatId,
    customerName: client.full_name ?? '',
    customerPhone: client.phone,
    customerEmail: client.email,
    source: client.source,
    externalId: client.external_id,
    status: 'reserved',
    operatorId,
    createdAt: new Date().toISOString(),
    acceptedAt: null,
    closedAt: null,
    messages: [],
    rating: null,
  };
}

/** Маппинг сообщения истории -> ChatMessage. */
function mapHistoryMessage(
  m: HistoryMessageItem,
  chatId: number,
  senderMap: Record<number, SenderRole>,
): ChatMessage {
  return {
    id: m.id,
    chatId,
    sender: senderMap[m.sender_type_id] ?? 'system',
    text: m.text,
    createdAt: m.created_at,
  };
}

/** Чаты текущего оператора (статусы reserved и active), без сообщений. */
export async function listMyChats(operatorId: number | null): Promise<ChatSession[]> {
  const data = await apiFetch<MyChatsResponse>('/chats/my');
  return data.items.map((it) => mapChat(it, operatorId));
}

/** Строит query-строку для постраничных списков с опциональным поиском. */
function pageQuery(page: number, search: string): string {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (search.trim()) params.set('search', search.trim());
  return params.toString();
}

/** Завершённые чаты текущего оператора (постранично, с поиском). */
export async function listClosed(
  operatorId: number | null,
  page = 1,
  search = '',
): Promise<PagedChats> {
  const data = await apiFetch<ClosedChatsResponse>(`/chats/closed?${pageQuery(page, search)}`);
  return {
    items: data.items.map((it) => mapClosedChat(it, operatorId)),
    total: data.total,
    page: data.page,
    pageSize: data.page_size,
  };
}

/** История сообщений чата. */
export async function getHistory(
  chatId: number,
  senderMap: Record<number, SenderRole>,
): Promise<ChatMessage[]> {
  const data = await apiFetch<HistoryResponse>(`/chats/${chatId}/history`);
  return data.items.map((m) => mapHistoryMessage(m, chatId, senderMap));
}

/** Оператор принимает зарезервированный чат. */
export async function acceptChat(chatId: number): Promise<void> {
  await apiFetch(`/chats/${chatId}/accept`, { method: 'POST' });
}

/** Оператор отклоняет чат (переназначается другому). */
export async function rejectChat(chatId: number): Promise<void> {
  await apiFetch(`/chats/${chatId}/reject`, { method: 'POST' });
}

/** Закрывает чат от лица оператора. */
export async function closeChat(chatId: number): Promise<void> {
  await apiFetch(`/chats/${chatId}/close`, {
    method: 'POST',
    body: JSON.stringify({ closed_by: 'operator' }),
  });
}

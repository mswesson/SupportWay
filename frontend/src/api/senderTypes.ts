// Справочник типов отправителя: нужен для маппинга sender_type_id из истории сообщений.

import { apiFetch } from './http';
import { SenderRole } from '../types';

interface SenderTypeItem {
  id: number;
  code: string;
  name: string;
}

interface SenderTypeListResponse {
  items: SenderTypeItem[];
}

/** Переводит код отправителя бэкенда в роль UI (client -> customer). */
export function codeToRole(code: string): SenderRole {
  if (code === 'operator') return 'operator';
  if (code === 'client') return 'customer';
  return 'system';
}

/** Загружает карту sender_type_id -> роль UI. */
export async function loadSenderTypeMap(): Promise<Record<number, SenderRole>> {
  const data = await apiFetch<SenderTypeListResponse>('/sender-types?page=1&page_size=100');
  const map: Record<number, SenderRole> = {};
  for (const item of data.items) {
    map[item.id] = codeToRole(item.code);
  }
  return map;
}

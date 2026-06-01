// Присутствие и статус оператора.

import { apiFetch } from './http';

interface OperatorMeResponse {
  operator_id: number;
  status: string;
  active_chats_count: number;
}

interface OperatorStatusResponse {
  operator_id: number;
  status: string;
}

export interface OperatorPresence {
  id: number;
  status: 'online' | 'offline';
  activeChatsCount: number;
}

function normalizeStatus(status: string): 'online' | 'offline' {
  return status === 'online' ? 'online' : 'offline';
}

/** Возвращает статус и нагрузку текущего оператора. */
export async function getMe(): Promise<OperatorPresence> {
  const data = await apiFetch<OperatorMeResponse>('/operators/me');
  return {
    id: data.operator_id,
    status: normalizeStatus(data.status),
    activeChatsCount: data.active_chats_count,
  };
}

/** Переключает статус оператора (онлайн/офлайн) и возвращает новый статус. */
export async function setStatus(online: boolean): Promise<'online' | 'offline'> {
  const data = await apiFetch<OperatorStatusResponse>('/operators/status', {
    method: 'POST',
    body: JSON.stringify({ online }),
  });
  return normalizeStatus(data.status);
}

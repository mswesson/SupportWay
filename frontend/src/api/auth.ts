// Авторизация оператора.

import { apiFetch, setToken } from './http';

interface LoginResponse {
  access_token: string;
  token_type: string;
}

/** Логинит оператора по ФИО и паролю, сохраняет JWT и возвращает токен. */
export async function login(fullName: string, password: string): Promise<string> {
  const data = await apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ full_name: fullName, password }),
  });
  setToken(data.access_token);
  return data.access_token;
}

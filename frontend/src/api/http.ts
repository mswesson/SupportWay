// Базовый HTTP-слой: абсолютный URL бэкенда, JWT-токен, обёртка над fetch.

// Адрес бэкенда. Можно переопределить через VITE_API_BASE; по умолчанию локальный :8080.
const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8080') + '/api/v1';

const TOKEN_KEY = 'support_token';
let authToken: string | null = localStorage.getItem(TOKEN_KEY);

/** Текущий JWT оператора (или null). */
export function getToken(): string | null {
  return authToken;
}

/** Сохраняет/очищает JWT (в памяти и localStorage). */
export function setToken(token: string | null): void {
  authToken = token;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/** Строит WebSocket-URL от того же хоста, что и REST (http -> ws, https -> wss). */
export function wsUrl(path: string): string {
  return API_BASE.replace(/^http/, 'ws') + path;
}

/** Ошибка HTTP-запроса с кодом статуса и текстом detail от бэкенда. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

/** Выполняет запрос к API: подставляет токен, сериализует JSON, разбирает ошибки. */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      // тело не JSON — оставляем statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

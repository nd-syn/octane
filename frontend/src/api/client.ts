import type { AuthTokens, Message } from '../types';

const BASE = '';

let accessToken: string | null = localStorage.getItem('octane_at');
let refreshToken: string | null = localStorage.getItem('octane_rt');

function setTokens(at: string, rt: string) {
  accessToken = at;
  refreshToken = rt;
  localStorage.setItem('octane_at', at);
  localStorage.setItem('octane_rt', rt);
}

function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('octane_at');
  localStorage.removeItem('octane_rt');
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (accessToken) h['Authorization'] = `Bearer ${accessToken}`;
  return h;
}

async function request<T>(method: string, path: string, data?: unknown): Promise<{ status: number; body: T | null }> {
  const opts: RequestInit = { method, headers: headers() };
  if (data !== undefined) opts.body = JSON.stringify(data);

  let resp = await fetch(BASE + path, opts);
  let body: T | null = null;
  try { body = await resp.json(); } catch { /* ignore */ }

  if (resp.status === 401 && refreshToken && path !== '/api/auth/refresh') {
    const ok = await tryRefresh();
    if (ok) {
      opts.headers = headers();
      resp = await fetch(BASE + path, opts);
      try { body = await resp.json(); } catch { /* ignore */ }
    }
  }

  return { status: resp.status, body };
}

async function tryRefresh(): Promise<boolean> {
  try {
    const r = await fetch(BASE + '/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const data = await r.json();
    if (r.ok && data.access_token) {
      setTokens(data.access_token, data.refresh_token);
      return true;
    }
    clearTokens();
    return false;
  } catch {
    clearTokens();
    return false;
  }
}

export const api = {
  getToken: () => accessToken,
  isAuth: () => !!accessToken,
  clearTokens,

  async signup(username: string, password: string, displayName?: string) {
    return request<AuthTokens>('POST', '/api/auth/signup', { username, password, display_name: displayName });
  },

  async login(username: string, password: string) {
    const res = await request<AuthTokens>('POST', '/api/auth/login', { username, password });
    if (res.status === 200 && res.body) setTokens(res.body.access_token, res.body.refresh_token);
    return res;
  },

  async logout() {
    await request('POST', '/api/auth/logout', { refresh_token: refreshToken });
    clearTokens();
  },

  getMe: () => request<import('../types').User>('GET', '/api/users/me'),
  searchUsers: (q: string) => request<{ users: import('../types').User[] }>('GET', `/api/users/search?q=${encodeURIComponent(q)}`),
  getUser: (username: string) => request<import('../types').User>('GET', `/api/users/${encodeURIComponent(username)}`),
  follow: (id: number) => request('POST', `/api/follows/${id}`),
  unfollow: (id: number) => request('DELETE', `/api/follows/${id}`),
  getFollowers: () => request<{ users: import('../types').User[] }>('GET', '/api/follows/followers'),
  getFollowing: () => request<{ users: import('../types').User[] }>('GET', '/api/follows/following'),
  getConversations: () => request<{ conversations: import('../types').Conversation[] }>('GET', '/api/conversations'),
  createConversation: (userId: number) => request<import('../types').Conversation>('POST', '/api/conversations', { user_id: userId }),
  getConversation: (id: number) => request<import('../types').Conversation>('GET', `/api/conversations/${id}`),
  getMessages: (convId: number) => request<Message[]>('GET', `/api/conversations/${convId}/messages`),
  sendMessage: (convId: number, content: string) => request<Message>('POST', `/api/conversations/${convId}/messages`, { content }),
};

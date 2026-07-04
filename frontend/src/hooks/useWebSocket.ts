import { useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

interface WSMessage {
  type: string;
  message?: {
    id: number;
    conversation_id: number;
    sender_id: number;
    sender_username?: string;
    content: string;
    created_at: string;
  };
  conversation_id?: number;
  user_id?: number;
}

export function useWebSocket(onMessage: (data: WSMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const token = api.getToken();
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws?token=${token}`;

    wsRef.current = new WebSocket(url);
    wsRef.current.onmessage = (e) => {
      try { onMessageRef.current(JSON.parse(e.data)); } catch { /* ignore */ }
    };
    wsRef.current.onclose = () => setTimeout(connect, 3000);
  }, []);

  useEffect(() => {
    if (api.isAuth()) connect();
    return () => wsRef.current?.close();
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}

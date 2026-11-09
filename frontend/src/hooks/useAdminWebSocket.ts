import { useEffect, useRef, useState, useCallback } from 'react';
import type { WsMessage } from '../types';

interface UseAdminWebSocketProps {
  token: string | null;
  onMessage: (msg: WsMessage) => void;
}

export function useAdminWebSocket({ token, onMessage }: UseAdminWebSocketProps) {
  const [connected, setConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);
  const pingInterval = useRef<number | null>(null);
  const backoff = useRef(1000);
  const onMessageRef = useRef(onMessage);
  const active = useRef(false);

  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!token || !active.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = import.meta.env.VITE_WS_URL || `${protocol}//${host}/ws/admin?token=${token}`;
    
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setConnected(true);
      backoff.current = 1000;
      
      pingInterval.current = window.setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };

    ws.current.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        onMessageRef.current(msg);
      } catch (e) {
        console.error('Failed to parse admin WS message', e);
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      if (pingInterval.current) clearInterval(pingInterval.current);
      
      if (!active.current) return;
      reconnectTimeout.current = window.setTimeout(() => {
        backoff.current = Math.min(backoff.current * 1.5, 30000);
        connect();
      }, backoff.current);
    };

    ws.current.onerror = (error) => {
      console.error('Admin WebSocket error:', error);
      ws.current?.close();
    };
  }, [token]);

  useEffect(() => {
    active.current = true;
    connect();
    return () => {
      active.current = false;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (pingInterval.current) clearInterval(pingInterval.current);
      ws.current?.close();
    };
  }, [connect]);

  return { connected };
}

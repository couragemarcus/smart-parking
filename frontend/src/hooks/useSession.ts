import { useState, useEffect, useCallback } from 'react';
import type { VisitorSession } from '../types';
import { api } from '../api/client';

export function useSession() {
  const [token, setTokenState] = useState<string | null>(localStorage.getItem('visitor_token'));
  const [session, setSession] = useState<VisitorSession | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const setToken = (newToken: string | null) => {
    if (newToken) {
      localStorage.setItem('visitor_token', newToken);
    } else {
      localStorage.removeItem('visitor_token');
    }
    setTokenState(newToken);
  };

  const loadSession = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await api.visitor.getMe();
      setSession(data);
      setError(null);
    } catch (err: any) {
      if (err.response?.status === 401 || err.response?.status === 404) {
        setToken(null);
        setSession(null);
      } else {
        setError(err.message || 'Failed to load session');
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const createSession = async () => {
    setLoading(true);
    try {
      const res = await api.visitor.createSession();
      setToken(res.token);
      await loadSession();
    } catch (err: any) {
      setError(err.message || 'Failed to create session');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const markArrived = async () => {
    try {
      const data = await api.visitor.markArrived();
      setSession(data);
    } catch (err: any) {
      setError(err.message || 'Failed to mark as arrived');
      throw err;
    }
  };

  const clearSession = () => {
    setToken(null);
    setSession(null);
  };

  return {
    token,
    session,
    loading,
    error,
    createSession,
    markArrived,
    refreshSession: loadSession,
    clearToken: clearSession,
  };
}

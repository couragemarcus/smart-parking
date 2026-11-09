import axios from 'axios';
import type {
  VisitorSession,
  ParkingSpace,
  ParkingLayout,
  DestinationInfo,
  SpaceState,
  AuditLog,
} from '../types';

const BASE = import.meta.env.VITE_API_URL ?? '';

const http = axios.create({ baseURL: `${BASE}/api` });

// ── Request interceptors ─────────────────────────────────────────────────────

http.interceptors.request.use((config) => {
  const visitorToken = localStorage.getItem('visitor_token');
  const adminToken = localStorage.getItem('admin_token');

  if (visitorToken) {
    // Attach to visitor endpoints and parking (public, token optional)
    config.headers['X-Visitor-Token'] = visitorToken;
  }
  if (adminToken) {
    config.headers['Authorization'] = `Bearer ${adminToken}`;
  }
  return config;
});

// ── Response interceptors ────────────────────────────────────────────────────

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      const url: string = err.config?.url ?? '';
      if (url.includes('/admin') || url.includes('/auth')) {
        localStorage.removeItem('admin_token');
        if (!window.location.pathname.startsWith('/admin')) {
          window.location.href = '/admin';
        }
      }
    }
    return Promise.reject(err);
  }
);

// ── Typed API surface ────────────────────────────────────────────────────────

export const api = {
  visitor: {
    /** POST /api/visitor/sessions — create anonymous session */
    createSession: async (): Promise<{ token: string; id: number }> => {
      const { data } = await http.post<VisitorSession>('/visitor/sessions');
      return { token: data.token, id: data.id };
    },

    /** GET /api/visitor/me */
    getMe: async (): Promise<VisitorSession> => {
      const { data } = await http.get<VisitorSession>('/visitor/me');
      return data;
    },

    /** POST /api/visitor/arrived */
    markArrived: async (): Promise<VisitorSession> => {
      const { data } = await http.post<VisitorSession>('/visitor/arrived');
      return data;
    },

    /** GET /api/visitor/assignment */
    getAssignment: async (): Promise<{ space: ParkingSpace | null; session: VisitorSession }> => {
      const { data } = await http.get('/visitor/assignment');
      return data;
    },
  },

  parking: {
    /** GET /api/parking/destination */
    getDestination: async (): Promise<DestinationInfo> => {
      const { data } = await http.get<DestinationInfo>('/parking/destination');
      return data;
    },

    /** GET /api/parking/layout */
    getLayout: async (): Promise<ParkingLayout> => {
      const { data } = await http.get<ParkingLayout>('/parking/layout');
      return data;
    },
  },

  admin: {
    /** POST /api/auth/login/json */
    login: async (username: string, password: string): Promise<{ access_token: string; role: string }> => {
      const { data } = await http.post<{ access_token: string; role: string }>(
        '/auth/login/json',
        { username, password }
      );
      return data;
    },

    /** GET /api/admin/parking/spaces */
    getSpaces: async (): Promise<ParkingSpace[]> => {
      const { data } = await http.get<ParkingSpace[]>('/admin/parking/spaces');
      return data;
    },

    /** PATCH /api/admin/parking/spaces/:id */
    updateSpace: async (id: number, state: SpaceState): Promise<void> => {
      await http.patch(`/admin/parking/spaces/${id}`, null, { params: { state } });
    },

    /** GET /api/admin/configuration */
    getConfig: async (): Promise<Record<string, string>> => {
      const { data } = await http.get<{ items: Record<string, string> }>('/admin/configuration');
      return data.items;
    },

    /** PATCH /api/admin/configuration */
    updateConfig: async (config: Record<string, unknown>): Promise<void> => {
      await http.patch('/admin/configuration', config);
    },

    /** GET /api/admin/events */
    getEvents: async (offset = 0, limit = 50): Promise<AuditLog[]> => {
      const { data } = await http.get<AuditLog[]>('/admin/events', {
        params: { offset, limit },
      });
      return data;
    },

    /** GET /api/admin/sessions */
    getSessions: async (): Promise<VisitorSession[]> => {
      const { data } = await http.get<VisitorSession[]>('/admin/sessions');
      return data;
    },

    /** POST /api/admin/match */
    matchArrival: async (session_id: number, arrival_event_id: number): Promise<void> => {
      await http.post('/admin/match', { session_id, arrival_event_id });
    },

    /** POST /api/admin/sessions/:id/depart */
    departSession: async (session_id: number): Promise<void> => {
      await http.post(`/admin/sessions/${session_id}/depart`);
    },

    /** GET /api/admin/qr */
    getQr: async (): Promise<{ qr_code_base64: string }> => {
      const { data } = await http.get<{ qr_code_base64: string }>('/admin/qr');
      return data;
    },
  },

  simulator: {
    /** POST /api/simulator/arrival */
    arrival: async (idempotency_key?: string): Promise<{
      status: string;
      idempotency_key: string;
      access?: 'GRANTED' | 'BLOCKED';
      session_matched?: boolean;
      space_name?: string | null;
    }> => {
      const { data } = await http.post('/simulator/arrival', { idempotency_key });
      return data;
    },

    /** POST /api/simulator/departure */
    departure: async (space_name: string): Promise<void> => {
      await http.post('/simulator/departure', { space_name });
    },

    /** POST /api/simulator/confirm-occupied */
    confirmOccupied: async (space_name: string): Promise<void> => {
      await http.post('/simulator/confirm-occupied', { space_name, occupied: true });
    },

    /** POST /api/simulator/reset */
    reset: async (): Promise<void> => {
      await http.post('/simulator/reset');
    },

    /** POST /api/simulator/expire-reservations */
    expireReservations: async (): Promise<void> => {
      await http.post('/simulator/expire-reservations');
    },
  },
};

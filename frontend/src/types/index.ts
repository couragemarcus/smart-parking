// ── Enumerations ────────────────────────────────────────────────────────────

export type SpaceState = 'AVAILABLE' | 'RESERVED' | 'OCCUPIED' | 'OUT_OF_SERVICE';
export type SessionState = 'WAITING' | 'ARRIVED' | 'ASSIGNED' | 'PARKED' | 'DEPARTED' | 'EXPIRED';

// ── Domain models ────────────────────────────────────────────────────────────

export interface ParkingSpace {
  id: number;
  name: string;
  position: number;
  state: SpaceState;
  session_id: number | null;
  reserved_at: string | null;
  occupied_at: string | null;
}

export interface VisitorSession {
  id: number;
  token: string;
  state: SessionState;
  space_id: number | null;
  arrived_at: string | null;
  assigned_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ParkingLayout {
  spaces: ParkingSpace[];
  total: number;
  available: number;
  occupied: number;
  reserved: number;
  out_of_service: number;
}

export interface DestinationInfo {
  institution_name: string;
  lat: number;
  lon: number;
  google_maps_url: string;
  waypoints: Array<{ lat: number; lon: number; label: string }> | null;
}

export interface AuditLog {
  id: number;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: string | null;
  timestamp: string;
}

// ── WebSocket message types ──────────────────────────────────────────────────

export type WsMessageType =
  | 'session_update'
  | 'layout_update'
  | 'assignment'
  | 'expired'
  | 'full'
  | 'ping'
  | 'reservations_expired'
  | 'allocation'
  | 'space_occupied'
  | 'space_vacated'
  | 'space_updated'
  | 'access_decision'
  | 'reset';

export interface WsMessage {
  type: WsMessageType;
  data?: unknown;
  // Common fields emitted by server
  space_name?: string;
  session_id?: number;
  released_space_ids?: number[];
  spaces?: number[];
  access?: 'GRANTED' | 'BLOCKED';
  arrival_event_id?: number;
  reason?: string;
}

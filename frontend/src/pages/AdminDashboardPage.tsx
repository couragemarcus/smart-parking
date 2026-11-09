import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAdminWebSocket } from '../hooks/useAdminWebSocket';
import { ParkingLayout } from '../components/ParkingLayout';
import type { ParkingSpace, VisitorSession, AuditLog, WsMessage } from '../types';

const AdminDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const token = localStorage.getItem('admin_token');
  
  const [spaces, setSpaces] = useState<ParkingSpace[]>([]);
  const [sessions, setSessions] = useState<VisitorSession[]>([]);
  const [events, setEvents] = useState<AuditLog[]>([]);
  const [qr, setQr] = useState<{ qr_code_base64: string } | null>(null);

  useEffect(() => {
    if (!token) {
      navigate('/admin');
      return;
    }
    loadData();
    loadQr();
  }, [token, navigate]);

  const loadData = async () => {
    try {
      const sp = await api.admin.getSpaces();
      setSpaces(sp);
      const sess = await api.admin.getSessions();
      setSessions(sess);
      const evts = await api.admin.getEvents(0, 10);
      setEvents(evts);
    } catch (err) {
      console.error(err);
    }
  };

  const loadQr = async () => {
    try {
      const q = await api.admin.getQr();
      setQr(q);
    } catch (err) {
      console.error(err);
    }
  };

  const handleWsMessage = (msg: WsMessage) => {
    if (msg.type === 'layout_update') setSpaces(msg.data as ParkingSpace[]);
    if (msg.type === 'session_update' || msg.type === 'assignment') {
      api.admin.getSessions().then(setSessions);
    }
  };

  const { connected } = useAdminWebSocket({ token, onMessage: handleWsMessage });

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    navigate('/admin');
  };

  const stats = {
    total: spaces.length,
    available: spaces.filter(s => s.state === 'AVAILABLE').length,
    occupied: spaces.filter(s => s.state === 'OCCUPIED').length,
    reserved: spaces.filter(s => s.state === 'RESERVED').length,
    oos: spaces.filter(s => s.state === 'OUT_OF_SERVICE').length,
  };

  return (
    <div className="admin-console">
      <aside className="admin-rail">
        <div className="admin-brand"><span className="brand-icon">P</span><span><strong>SmartPark</strong><small>Security console</small></span></div>
        <div className="admin-rail-label">Workspace</div>
        <div className="admin-nav-item active">◉ <span>Live view</span></div>
        <div className="admin-nav-item">♙ <span>Visitor queue</span></div>
        <div className="admin-nav-item">▣ <span>Parking status</span></div>
        <div className="admin-nav-item">◷ <span>Activity logs</span></div>
        <div className="admin-nav-item">⚙ <span>Settings</span></div>
        <button onClick={handleLogout} className="admin-logout">↪ <span>Logout</span></button>
      </aside>
      <main className="admin-main">
        <header className="admin-topbar">
          <div><div className="eyebrow">Operations</div><h1>Security dashboard</h1></div>
          <div className={`connection-pill ${connected ? 'is-live' : 'is-offline'}`}>
            {connected ? '● WS Connected' : '○ WS Offline'}
          </div>
        </header>

        <div className="admin-stats">
          <div><span className="stat-icon red">●</span><strong>{stats.occupied} / {stats.total}</strong><small>Occupied</small></div>
          <div><span className="stat-icon green">●</span><strong>{stats.available}</strong><small>Available</small></div>
          <div><span className="stat-icon blue">♟</span><strong>{sessions.length}</strong><small>Today's visitors</small></div>
          <div><span className="stat-icon gray">◷</span><strong>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong><small>Last activity</small></div>
        </div>

        <div className="admin-grid">
          <div className="admin-live-panel">
            <div className="admin-panel-heading"><div><div className="section-kicker">Parking lot</div><h2>Live view</h2></div><span className="live-chip">● Online</span></div>
            <ParkingLayout spaces={spaces} showLabels={true} />
          </div>

          <div className="admin-activity-panel">
            <div className="admin-panel-heading"><div><div className="section-kicker">System feed</div><h2>Recent activity</h2></div><span className="view-all">View all</span></div>
            <div className="activity-list">
              {events.slice(0, 5).map(e => (
                <div key={e.id} className="activity-item"><span className="activity-time">{new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><div><strong>{e.action.replace(/_/g, ' ')}</strong><small>{e.detail || e.entity_type}</small></div></div>
              ))}
              {events.length === 0 && <div className="empty-state">No activity recorded yet.</div>}
            </div>
          </div>

          <div className="admin-queue-panel">
            <div className="admin-panel-heading"><div><div className="section-kicker">Arrivals</div><h2>Visitor queue</h2></div><span className="panel-tag">{sessions.filter(s => s.state === 'ARRIVED').length} waiting</span></div>
            <div className="session-list">
              {sessions.filter(s => s.state !== 'DEPARTED').slice(0, 6).map(s => (
                <div key={s.id} className="session-row"><span className={`session-state ${s.state.toLowerCase()}`} /> <strong>Visitor #{s.id}</strong><span>{s.space_id ? `L${s.space_id}` : s.state}</span></div>
              ))}
              {sessions.length === 0 && <div className="empty-state">No active visitor sessions.</div>}
            </div>
          </div>

          {qr && (
            <div className="admin-qr-panel">
              <div><div className="section-kicker">Front desk</div><h2>Visitor QR</h2><p>Scan to open the arrival portal.</p></div>
              <img src={`data:image/png;base64,${qr.qr_code_base64}`} alt="Visitor QR" />
            </div>
          )}

        </div>
      </main>
    </div>
  );
};

export default AdminDashboardPage;

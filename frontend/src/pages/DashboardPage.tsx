import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../hooks/useSession';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../api/client';
import { ParkingLayout } from '../components/ParkingLayout';
import { StatusBanner } from '../components/StatusBanner';
import type { ParkingSpace, WsMessage } from '../types';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { token, session, loading, error: sessionError, markArrived, clearToken, refreshSession } = useSession();
  
  const [spaces, setSpaces] = useState<ParkingSpace[]>([]);
  const [assignedSpace, setAssignedSpace] = useState<ParkingSpace | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleWsMessage = (msg: WsMessage) => {
    if (msg.type === 'session_update' || msg.type === 'assignment' || msg.type === 'expired') {
      refreshSession();
    }
    if (msg.type === 'layout_update') {
      setSpaces(msg.data as ParkingSpace[]);
    }
    if (msg.type === 'assignment') {
      // Refresh assignment specifically
      loadAssignment();
    }
  };

  const { connected } = useWebSocket({ token, onMessage: handleWsMessage });

  const loadAssignment = async () => {
    try {
      const { space } = await api.visitor.getAssignment();
      setAssignedSpace(space);
    } catch (err) {
      console.error('Failed to load assignment', err);
    }
  };

  const loadLayout = async () => {
    try {
      const layout = await api.parking.getLayout();
      setSpaces(layout.spaces);
    } catch (err) {
      console.error('Failed to load layout', err);
    }
  };

  useEffect(() => {
    if (!loading && !token) {
      navigate('/');
    }
  }, [loading, token, navigate]);

  useEffect(() => {
    if (token) {
      loadLayout();
      loadAssignment();
    }
  }, [token]);

  const handleArrive = async () => {
    setError(null);
    try {
      await markArrived();
    } catch (err: any) {
      setError(err.message || 'Failed to mark as arrived');
    }
  };

  const handleNewSession = () => {
    clearToken();
    navigate('/');
  };

  if (loading) return <div className="text-center p-8 text-xl">Loading session...</div>;
  if (!session) return <div className="text-center p-8 text-red-500">Session not found. Redirecting...</div>;

  return (
    <div className="visitor-page">
      <div className="page-heading">
        <div><div className="eyebrow">Private visitor pass</div><h1>Your parking session</h1></div>
        <div className={`connection-pill ${connected ? 'is-live' : 'is-offline'}`}>
          {connected ? '● Live' : '○ Offline'}
        </div>
      </div>

      {(sessionError || error) && (
        <div className="error-strip">
          {sessionError || error}
        </div>
      )}

      <StatusBanner 
        sessionState={session.state} 
        spaceName={assignedSpace?.name} 
        expiresAt={session.expires_at} 
      />

      {session.state === 'WAITING' && (
        <button
          onClick={handleArrive}
          className="primary-action mb-8"
        >
          I Have Arrived
        </button>
      )}

      {['DEPARTED', 'EXPIRED'].includes(session.state) && (
        <button
          onClick={handleNewSession}
          className="secondary-action full-action mb-8"
        >
          Start New Session
        </button>
      )}

      <div className="surface-panel">
        <div className="panel-heading"><div><div className="section-kicker">Live wayfinding</div><h2>Find your bay</h2></div><span className="panel-tag">L1 — L4</span></div>
        <ParkingLayout 
          spaces={spaces} 
          assignedSpaceId={session.space_id} 
          showLabels={false} 
        />
        <p className="text-gray-500 text-sm mt-4 text-center italic">
          For your privacy, only your assigned space is labelled.
        </p>
      </div>
    </div>
  );
};

export default DashboardPage;

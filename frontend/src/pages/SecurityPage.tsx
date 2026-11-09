import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAdminWebSocket } from '../hooks/useAdminWebSocket';
import type { VisitorSession, ParkingSpace, WsMessage } from '../types';

const SecurityPage: React.FC = () => {
  const navigate = useNavigate();
  const token = localStorage.getItem('admin_token');
  
  const [sessions, setSessions] = useState<VisitorSession[]>([]);
  const [spaces, setSpaces] = useState<ParkingSpace[]>([]);
  const [accessDecision, setAccessDecision] = useState<WsMessage | null>(null);

  useEffect(() => {
    if (!token) {
      navigate('/admin');
      return;
    }
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [token, navigate]);

  const loadData = useCallback(async () => {
    try {
      const sess = await api.admin.getSessions();
      setSessions(sess);
      const sp = await api.admin.getSpaces();
      setSpaces(sp);
    } catch (err) {
      console.error(err);
    }
  }, []);

  const handleMessage = useCallback((message: WsMessage) => {
    if (message.type === 'access_decision') {
      setAccessDecision(message);
      loadData();
    }
    if (['allocation', 'space_occupied', 'space_vacated', 'reset'].includes(message.type)) {
      loadData();
    }
  }, [loadData]);

  useAdminWebSocket({ token, onMessage: handleMessage });

  const handleManualDepart = async (id: number) => {
    try {
      await api.admin.departSession(id);
      loadData();
    } catch (err) {
      alert('Failed to depart session');
    }
  };

  const pendingArrivals = sessions.filter(s => s.state === 'ARRIVED');
  const parked = sessions.filter(s => s.state === 'PARKED');

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Security View</h1>

      {accessDecision && (
        <div
          className={`mb-6 rounded-xl border-2 p-5 shadow ${
            accessDecision.access === 'GRANTED'
              ? 'border-green-300 bg-green-50 text-green-900'
              : 'border-red-300 bg-red-50 text-red-900'
          }`}
          role="status"
          aria-live="assertive"
        >
          <div className="text-sm font-bold uppercase tracking-wide">Latest sensor decision</div>
          <div className="mt-1 text-2xl font-black">
            {accessDecision.access === 'GRANTED' ? 'ACCESS GRANTED' : 'ACCESS BLOCKED'}
          </div>
          <p className="mt-1">
            {accessDecision.access === 'GRANTED'
              ? `Vehicle matched and assigned ${accessDecision.space_name}.`
              : 'No queued visitor could be safely matched, or the lot is full. Security must verify the vehicle before allowing entry.'}
          </p>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4 text-yellow-600">Pending Arrivals (Gate)</h2>
          {pendingArrivals.length === 0 ? (
            <p className="text-gray-500">No vehicles waiting at gate.</p>
          ) : (
            <div className="space-y-4">
              {pendingArrivals.map(s => (
                <div key={s.id} className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="font-bold text-lg mb-2">Session #{s.id}</div>
                  <div className="text-sm text-gray-600 mb-2">
                    Arrived: {s.arrived_at ? new Date(s.arrived_at).toLocaleTimeString() : 'N/A'}
                  </div>
                  <p className="text-sm italic text-gray-500">Waiting for hardware sensor detection...</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4 text-green-600">Currently Parked</h2>
          {parked.length === 0 ? (
            <p className="text-gray-500">No parked vehicles.</p>
          ) : (
            <div className="space-y-4">
              {parked.map(s => (
                <div key={s.id} className="p-4 bg-green-50 rounded-lg border border-green-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold">Session #{s.id}</div>
                    <div className="text-sm">Space ID: {s.space_id}</div>
                  </div>
                  <button 
                    onClick={() => handleManualDepart(s.id)}
                    className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm shadow"
                  >
                    Mark Departed
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SecurityPage;

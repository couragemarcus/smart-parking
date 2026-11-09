import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ParkingLayout } from '../components/ParkingLayout';
import { Toast } from '../components/Toast';
import type { ParkingSpace, VisitorSession } from '../types';

const SimulatorPage: React.FC = () => {
  const [spaces, setSpaces] = useState<ParkingSpace[]>([]);
  const [sessions, setSessions] = useState<VisitorSession[]>([]);
  const [toast, setToast] = useState<{ message: string; variant: 'success'|'error'|'info' } | null>(null);

  const loadData = async () => {
    try {
      const layout = await api.parking.getLayout();
      setSpaces(layout.spaces);
      const sess = await api.admin.getSessions();
      setSessions(sess);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleArrival = async () => {
    try {
      const res = await api.simulator.arrival();
      if (res.session_matched) {
        setToast({ message: `Arrival matched! Space assigned: ${res.space_name}`, variant: 'success' });
      } else {
        setToast({ message: 'Arrival recorded, but no waiting sessions found.', variant: 'info' });
      }
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || 'Error simulating arrival', variant: 'error' });
    }
  };

  const handleSpaceAction = async (space: ParkingSpace) => {
    try {
      if (space.state === 'RESERVED') {
        await api.simulator.confirmOccupied(space.name);
        setToast({ message: `${space.name} marked as occupied`, variant: 'success' });
      } else if (space.state === 'OCCUPIED') {
        await api.simulator.departure(space.name);
        setToast({ message: `${space.name} departed`, variant: 'success' });
      } else if (space.state === 'OUT_OF_SERVICE') {
        await api.admin.updateSpace(space.id, 'AVAILABLE');
        setToast({ message: `${space.name} is now available`, variant: 'success' });
      } else if (space.state === 'AVAILABLE') {
        await api.admin.updateSpace(space.id, 'OUT_OF_SERVICE');
        setToast({ message: `${space.name} is now out of service`, variant: 'info' });
      }
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || 'Action failed', variant: 'error' });
    }
  };

  const handleReset = async () => {
    try {
      await api.simulator.reset();
      setToast({ message: 'System reset completely', variant: 'success' });
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || 'Reset failed', variant: 'error' });
    }
  };

  const handleExpire = async () => {
    try {
      await api.simulator.expireReservations();
      setToast({ message: 'Reservations expired', variant: 'info' });
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || 'Expire failed', variant: 'error' });
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Hardware Simulator</h1>
      
      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
            <h2 className="text-xl font-bold mb-4">Parking Lot View</h2>
            <ParkingLayout spaces={spaces} showLabels={true} onSpaceClick={handleSpaceAction} />
            <p className="text-sm text-gray-500 mt-4 text-center">
              Click on a space to change its state. (Available ↔ Out of Service, Reserved → Occupied, Occupied → Depart)
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow border border-gray-200 flex flex-wrap gap-4">
            <button onClick={handleArrival} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded shadow">
              🚙 Simulate Sensor Arrival
            </button>
            <button onClick={handleExpire} className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded shadow">
              ⏳ Expire Reservations
            </button>
            <button onClick={handleReset} className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded shadow ml-auto">
              ⚠️ Reset System
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl shadow border border-gray-200 h-full max-h-[600px] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Active Sessions</h2>
            {sessions.filter(s => !['DEPARTED', 'EXPIRED'].includes(s.state)).length === 0 ? (
              <p className="text-gray-500 italic">No active sessions.</p>
            ) : (
              <div className="space-y-3">
                {sessions.filter(s => !['DEPARTED', 'EXPIRED'].includes(s.state)).map(s => (
                  <div key={s.id} className="p-3 bg-gray-50 rounded border border-gray-100 text-sm">
                    <div className="font-bold">ID: {s.id} <span className="ml-2 font-mono text-xs bg-gray-200 px-1 rounded">{s.state}</span></div>
                    {s.space_id && <div className="text-gray-600">Space ID: {s.space_id}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimulatorPage;

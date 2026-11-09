import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapView } from '../components/MapView';
import { api } from '../api/client';
import { useSession } from '../hooks/useSession';
import type { DestinationInfo } from '../types';

const WelcomePage: React.FC = () => {
  const navigate = useNavigate();
  const { token, session, loading: sessionLoading, createSession } = useSession();
  
  const [destination, setDestination] = useState<DestinationInfo | null>(null);
  const [userLoc, setUserLoc] = useState<{lat: number; lon: number} | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!sessionLoading && token && session && !['DEPARTED', 'EXPIRED'].includes(session.state)) {
      navigate('/dashboard');
    }
  }, [token, session, sessionLoading, navigate]);

  useEffect(() => {
    const fetchDest = async () => {
      try {
        const dest = await api.parking.getDestination();
        setDestination(dest);
      } catch (err: any) {
        setError('Failed to load destination info.');
      } finally {
        setLoading(false);
      }
    };
    fetchDest();

    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setUserLoc({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        (err) => console.warn('Geolocation blocked or failed:', err),
        { timeout: 10000 }
      );
    }
  }, []);

  const handleStart = async () => {
    setStarting(true);
    setError('');
    try {
      await createSession();
      navigate('/dashboard');
    } catch (err) {
      setError('Failed to start session. Please try again.');
      setStarting(false);
    }
  };

  if (sessionLoading || loading) return <div className="text-center p-8">Loading...</div>;

  return (
    <div className="welcome-page">
      <div className="welcome-hero">
        <div className="eyebrow"><span className="live-dot" /> Visitor arrival portal</div>
        <h1>Park once.<br /><em>Move with confidence.</em></h1>
        <p>Scan in, get directions, and receive a private bay assignment when your arrival is confirmed.</p>
      </div>

      <div className="welcome-content">
        {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}
        
        {destination && (
          <div className="destination-block">
            <div className="section-kicker">Your destination</div>
            <h2>{destination.institution_name}</h2>
            <div className="map-frame">
              <MapView 
                parkingLat={destination.lat} 
                parkingLon={destination.lon}
                userLat={userLoc?.lat}
                userLon={userLoc?.lon}
                institutionName={destination.institution_name}
              />
            </div>
            
            <a 
              href={destination.google_maps_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="secondary-action"
            >
              🗺️ Get Directions in Maps
            </a>
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={starting}
          className={`primary-action ${
            starting ? 'is-loading' : ''
          }`}
        >
          {starting ? 'Starting...' : 'Start Parking Session'}
        </button>
      </div>
    </div>
  );
};

export default WelcomePage;

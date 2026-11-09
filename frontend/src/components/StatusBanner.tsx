import React from 'react';
import type { SessionState } from '../types';
import { CountdownTimer } from './CountdownTimer';

interface Props {
  sessionState: SessionState;
  spaceName?: string;
  expiresAt?: string | null;
}

export const StatusBanner: React.FC<Props> = ({ sessionState, spaceName, expiresAt }) => {
  let stateClass = '';
  let message = '';
  let icon = '';

  switch (sessionState) {
    case 'WAITING':
      stateClass = 'state-waiting';
      icon = '📍';
      message = 'Session active. Tap "I Have Arrived" when you reach the entrance.';
      break;
    case 'ARRIVED':
      stateClass = 'state-arrived';
      icon = '⏳';
      message = 'Waiting for vehicle detection by sensor...';
      break;
    case 'ASSIGNED':
      stateClass = 'state-assigned';
      icon = '✅';
      message = `Space reserved! Proceed to ${spaceName || 'your space'}.`;
      break;
    case 'PARKED':
      stateClass = 'state-parked';
      icon = '🚗';
      message = 'Parking confirmed. Welcome!';
      break;
    case 'DEPARTED':
      stateClass = 'state-departed';
      icon = '👋';
      message = 'Thank you for visiting!';
      break;
    case 'EXPIRED':
      stateClass = 'state-expired';
      icon = '❌';
      message = 'Reservation expired. Please contact security.';
      break;
  }

  return (
    <div className={`status-banner ${stateClass}`} role="alert" aria-live="polite">
      <div className="status-copy">
        <span className="status-icon" role="img" aria-hidden="true">{icon}</span>
        <div><span className="status-label">Current status</span><p>{message}</p></div>
      </div>
      {sessionState === 'ASSIGNED' && expiresAt && (
        <div className="status-countdown">
          <span>Expires in</span>
          <CountdownTimer expiresAt={expiresAt} />
        </div>
      )}
    </div>
  );
};

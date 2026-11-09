import React from 'react';
import { Link } from 'react-router-dom';

export const NavBar: React.FC = () => {
  return (
    <nav className="app-nav sticky top-0 z-50">
      <div className="nav-inner container mx-auto px-4">
        <Link to="/" className="brand-mark">
          <span className="brand-icon">P</span>
          <span><strong>SmartPark</strong><small>arrival control</small></span>
        </Link>
        <div className="nav-links">
          <Link to="/simulator">Simulator</Link>
          <Link to="/admin">Admin Login</Link>
        </div>
      </div>
    </nav>
  );
};

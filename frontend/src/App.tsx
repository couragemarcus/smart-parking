import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { NavBar } from './components/NavBar';

const WelcomePage = lazy(() => import('./pages/WelcomePage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage'));
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'));
const SecurityPage = lazy(() => import('./pages/SecurityPage'));
const SimulatorPage = lazy(() => import('./pages/SimulatorPage'));

const NotFoundPage = () => (
  <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
    <h1 className="text-4xl font-bold mb-4">404 - Not Found</h1>
    <p>The page you are looking for does not exist.</p>
  </div>
);

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="app-shell min-h-screen flex flex-col">
        <NavBar />
        <main className="app-main flex-grow container mx-auto px-4 py-8 max-w-7xl">
          <Suspense fallback={<div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div></div>}>
            <Routes>
              <Route path="/" element={<WelcomePage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/admin" element={<AdminLoginPage />} />
              <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
              <Route path="/admin/security" element={<SecurityPage />} />
              <Route path="/simulator" element={<SimulatorPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;

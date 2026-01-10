import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import '@/App.css';
import LoginPage from './pages/LoginPage';
import AdminDashboard from './pages/AdminDashboard';
import UserDashboard from './pages/UserDashboard';
import SendMessages from './pages/SendMessagesSimple';
import Templates from './pages/Templates';
import MyTemplates from './pages/MyTemplates';
import CampaignHistory from './pages/CampaignHistory';
import CampaignDetails from './pages/CampaignDetails';
import Settings from './pages/Settings';
import { Toaster } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import api from './utils/api';

const App = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('originalAdmin');
    setUser(null);
  };

  const handleImpersonate = (token, userData) => {
    // Save original admin info before switching
    const currentUser = JSON.parse(localStorage.getItem('user'));
    const currentToken = localStorage.getItem('token');
    localStorage.setItem('originalAdmin', JSON.stringify({ user: currentUser, token: currentToken }));
    
    // Switch to impersonated user
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleStopImpersonation = async () => {
    try {
      const response = await api.post('/auth/stop-impersonation');
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      localStorage.removeItem('originalAdmin');
      setUser(response.data.user);
      toast.success('Returned to admin account');
    } catch (error) {
      // Fallback: use stored original admin data
      const originalAdmin = localStorage.getItem('originalAdmin');
      if (originalAdmin) {
        const { user: adminUser, token } = JSON.parse(originalAdmin);
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(adminUser));
        localStorage.removeItem('originalAdmin');
        setUser(adminUser);
        toast.success('Returned to admin account');
      } else {
        toast.error('Failed to return to admin account');
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="App">
      {/* Impersonation Banner */}
      {user?.isImpersonating && (
        <div className="bg-amber-500 text-white px-4 py-2 text-center flex items-center justify-center gap-4 sticky top-0 z-50">
          <span className="font-medium">
            👤 You are viewing as: <strong>{user.email}</strong>
          </span>
          <Button 
            size="sm" 
            variant="secondary"
            onClick={handleStopImpersonation}
            className="bg-white text-amber-600 hover:bg-amber-50"
          >
            Return to Admin
          </Button>
        </div>
      )}
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              user ? (
                <Navigate to={user.role === 'admin' && !user.isImpersonating ? '/admin' : '/dashboard'} />
              ) : (
                <LoginPage onLogin={handleLogin} />
              )
            }
          />
          <Route
            path="/admin"
            element={
              user && user.role === 'admin' ? (
                <AdminDashboard user={user} onLogout={handleLogout} onImpersonate={handleImpersonate} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/dashboard"
            element={
              user ? (
                <UserDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/send"
            element={
              user ? (
                <SendMessages user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/templates"
            element={
              user ? (
                <Templates user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/my-templates"
            element={
              user ? (
                <MyTemplates user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/campaigns"
            element={
              user ? (
                <CampaignHistory user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/campaigns/:id"
            element={
              user ? (
                <CampaignDetails user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/settings"
            element={
              user ? (
                <Settings user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          />
          <Route
            path="/"
            element={
              <Navigate to={user ? (user.role === 'admin' ? '/admin' : '/dashboard') : '/login'} />
            }
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
};

export default App;
'use client';

import { useState, useEffect } from 'react';
import { Dashboard } from '@/components/dashboard';
import { LandingPage } from '@/components/landing/landing-page';
import { LoginForm } from '@/components/auth/login-form';
import { useAuth } from '@/lib/auth-context';

export default function Home() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [showDashboard, setShowDashboard] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user has visited before
    const hasVisited = localStorage.getItem('sdlc-agent-visited');
    if (hasVisited) {
      setShowDashboard(true);
    }
    setIsLoading(false);
  }, []);

  const handleGetStarted = () => {
    localStorage.setItem('sdlc-agent-visited', 'true');
    setShowLogin(true);
  };

  const handleShowLanding = () => {
    setShowDashboard(false);
    setShowLogin(false);
  };

  const handleLoginSuccess = () => {
    setShowLogin(false);
    setShowDashboard(true);
  };

  if (isLoading || authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  // If user wants to see dashboard but isn't authenticated, show login
  if (showDashboard && !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="w-full max-w-md p-4">
          <LoginForm onSuccess={handleLoginSuccess} />
          <button
            onClick={handleShowLanding}
            className="mt-4 w-full text-center text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back to home
          </button>
        </div>
      </div>
    );
  }

  // Show login page
  if (showLogin && !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="w-full max-w-md p-4">
          <LoginForm onSuccess={handleLoginSuccess} />
          <button
            onClick={handleShowLanding}
            className="mt-4 w-full text-center text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back to home
          </button>
        </div>
      </div>
    );
  }

  if (showDashboard || isAuthenticated) {
    return <Dashboard onShowLanding={handleShowLanding} />;
  }

  return <LandingPage onGetStarted={handleGetStarted} />;
}

'use client';

import { useState, useEffect } from 'react';
import { Dashboard } from '@/components/dashboard';
import { LandingPage } from '@/components/landing/landing-page';

export default function Home() {
  const [showDashboard, setShowDashboard] = useState(false);
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
    setShowDashboard(true);
  };

  const handleShowLanding = () => {
    setShowDashboard(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (showDashboard) {
    return <Dashboard onShowLanding={handleShowLanding} />;
  }

  return <LandingPage onGetStarted={handleGetStarted} />;
}

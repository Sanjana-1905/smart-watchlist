import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
  /**
   * true (default): route requires onboarding to be complete — redirects
   * incomplete users to /onboarding.
   * false: route IS the onboarding flow itself — redirects users who've
   * already completed it back to the dashboard, so it can't be revisited
   * as a way to silently reset the profile.
   */
  requireOnboarding?: boolean;
}

export default function ProtectedRoute({ children, requireOnboarding = true }: ProtectedRouteProps) {
  const { token, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Loading...
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (requireOnboarding && user && !user.onboarding_completed) {
    return <Navigate to="/onboarding" replace />;
  }

  if (!requireOnboarding && user && user.onboarding_completed) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

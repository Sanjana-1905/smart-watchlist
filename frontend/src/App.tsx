import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AppShell from './components/AppShell';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import ExplorePage from './pages/ExplorePage';
import StockDetail from './pages/StockDetail';

import ProfilePage from './pages/ProfilePage';
import UpdatesPage from './pages/UpdatesPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute requireOnboarding={false}>
                <OnboardingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppShell><DashboardPage /></AppShell>
              </ProtectedRoute>
            }
          />
          <Route path="/explore" element={<ProtectedRoute><AppShell><ExplorePage /></AppShell></ProtectedRoute>} />
          <Route path="/updates" element={<ProtectedRoute><AppShell><UpdatesPage /></AppShell></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><AppShell><ProfilePage /></AppShell></ProtectedRoute>} />
          <Route
            path="/stock/:symbol"
            element={
              <ProtectedRoute>
                <AppShell><StockDetail /></AppShell>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}


export default App;

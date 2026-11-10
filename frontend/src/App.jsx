import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import BottomNav from './components/BottomNav';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import ProfilePage from './pages/ProfilePage';
import FarmListPage from './pages/FarmListPage';
import FarmFormPage from './pages/FarmFormPage';
import WeatherPage from './pages/WeatherPage';
import SoilPage from './pages/SoilPage';
import ChatPage from './pages/ChatPage';
import MarketplacePage from './pages/MarketplacePage';
import AdminPage from './pages/AdminPage';
import { useAuth } from './context/AuthContext';

function AppLayout({ children }) {
  return (
    <div className="app-container">
      {children}
      <BottomNav />
    </div>
  );
}

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public route */}
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
        }
      />

      {/* Protected routes with bottom nav */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout>
              <HomePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/weather"
        element={
          <ProtectedRoute>
            <AppLayout>
              <WeatherPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/soil"
        element={
          <ProtectedRoute>
            <AppLayout>
              <SoilPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <AppLayout>
              <ChatPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/marketplace"
        element={
          <ProtectedRoute>
            <AppLayout>
              <MarketplacePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AppLayout>
              <AdminPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <AppLayout>
              <ProfilePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/farms"
        element={
          <ProtectedRoute>
            <AppLayout>
              <FarmListPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/farms/new"
        element={
          <ProtectedRoute>
            <AppLayout>
              <FarmFormPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/farms/:id/edit"
        element={
          <ProtectedRoute>
            <AppLayout>
              <FarmFormPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

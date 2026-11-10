import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('agritech_token'));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('agritech_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  const isAuthenticated = !!token;

  // On mount, verify token and fetch user profile if token exists
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const res = await api.get('/profile');
          const userData = res.data;
          setUser(userData);
          localStorage.setItem('agritech_user', JSON.stringify(userData));
        } catch (err) {
          // Token invalid, clear auth
          console.error('Auth check failed:', err);
          setToken(null);
          setUser(null);
          localStorage.removeItem('agritech_token');
          localStorage.removeItem('agritech_user');
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = (newToken, userData) => {
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('agritech_token', newToken);
    if (userData) {
      localStorage.setItem('agritech_user', JSON.stringify(userData));
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('agritech_token');
    localStorage.removeItem('agritech_user');
  };

  const updateUser = (userData) => {
    setUser(userData);
    localStorage.setItem('agritech_user', JSON.stringify(userData));
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated,
        loading,
        login,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;

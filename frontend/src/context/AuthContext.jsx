import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getMe } from '../api/repurpose';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [styles, setStyles] = useState([]);
  const [defaultStyleId, setDefaultStyleId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(() => localStorage.getItem('token'));

  const loadUserData = useCallback(async (authToken, { silent = false } = {}) => {
    if (!authToken) {
      setUser(null);
      setStyles([]);
      setDefaultStyleId(null);
      setLoading(false);
      return;
    }

    if (!silent) setLoading(true);
    try {
      const userData = await getMe(authToken);
      setUser({
        id: userData.id,
        email: userData.email,
        name: userData.name,
        avatar_url: userData.avatar_url,
      });
      setStyles(userData.styles || []);
      setDefaultStyleId(userData.default_style_id || null);
    } catch (err) {
      console.error('Failed to load user:', err);
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      setStyles([]);
      setDefaultStyleId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    if (urlToken) {
      localStorage.setItem('token', urlToken);
      setToken(urlToken);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    loadUserData(token);
  }, [token, loadUserData]);

  const login = (newToken) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setStyles([]);
    setDefaultStyleId(null);
  };

  const refetchUserData = useCallback(async () => {
    if (!token) return;
    await loadUserData(token, { silent: true });
  }, [token, loadUserData]);

  const addStyle = useCallback((style) => {
    setStyles((prev) => {
      if (prev.some((s) => s.id === style.id)) return prev;
      return [style, ...prev];
    });
    setDefaultStyleId(style.id);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        styles,
        defaultStyleId,
        token,
        loading,
        login,
        logout,
        refetchUserData,
        addStyle,
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

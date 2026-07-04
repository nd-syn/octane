import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { api } from '../api/client';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<string | null>;
  signup: (username: string, password: string, displayName?: string) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (api.isAuth()) {
      api.getMe().then(res => {
        if (res.status === 200 && res.body) setUser(res.body);
        else api.clearTokens();
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password);
    if (res.status === 200 && res.body) {
      const me = await api.getMe();
      if (me.status === 200 && me.body) setUser(me.body);
      return null;
    }
    return (res.body as any)?.detail || 'Invalid credentials';
  }, []);

  const signup = useCallback(async (username: string, password: string, displayName?: string) => {
    const res = await api.signup(username, password, displayName);
    if (res.status === 201 && res.body) {
      const me = await api.getMe();
      if (me.status === 200 && me.body) setUser(me.body);
      return null;
    }
    return (res.body as any)?.detail || 'Signup failed';
  }, []);

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}

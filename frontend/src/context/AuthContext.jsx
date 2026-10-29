import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "../api/client.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => { setUser(null); setSessionExpired(true); });
    if (!tokenStore.get()) return;
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.login({ email, password });
    tokenStore.set(res.access_token);
    setSessionExpired(false);
    setUser(res.user);
  }, []);

  const register = useCallback(async (name, email, password) => {
    await api.register({ name, email, password });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); setSessionExpired(false); }, []);

  const value = useMemo(() => ({ user, loading, sessionExpired, login, register, logout }), [user, loading, sessionExpired, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

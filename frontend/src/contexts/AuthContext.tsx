import { createContext, useContext, useMemo, useState, ReactNode } from "react";
import { getRoleFromToken, getEmailFromToken, type UserRole } from "@/lib/jwt";

interface AuthContextType {
  token: string | null;
  role: UserRole | null;
  email: string | null;
  isLoggedIn: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  role: null,
  email: null,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
});

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("certverify_token")
  );

  const role = useMemo(() => getRoleFromToken(token), [token]);
  const email = useMemo(() => getEmailFromToken(token), [token]);

  const login = (newToken: string) => {
    localStorage.setItem("certverify_token", newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem("certverify_token");
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{ token, role, email, isLoggedIn: !!token, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { ShieldCheck, Building2, UserCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import type { UserRole } from "@/lib/jwt";
import { cn } from "@/lib/utils";
import { AxiosError } from "axios";

const LoginPage = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [registerRole, setRegisterRole] = useState<UserRole>("institution");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const isTransientNetworkError = (err: unknown): boolean => {
    const axiosErr = err as AxiosError;
    if (!axiosErr || !axiosErr.isAxiosError) return false;
    if (axiosErr.code === "ERR_NETWORK" || axiosErr.code === "ECONNABORTED") return true;
    if (!axiosErr.response) return true;
    const status = axiosErr.response.status;
    return status === 502 || status === 503 || status === 504;
  };

  const fetchTokenWithRetry = async (attempts = 5): Promise<string> => {
    let lastError: unknown = null;
    for (let i = 0; i < attempts; i += 1) {
      try {
        return await fetchToken();
      } catch (err: unknown) {
        lastError = err;
        if (!isTransientNetworkError(err) || i === attempts - 1) {
          throw err;
        }
        await sleep(1500 * (i + 1));
      }
    }
    throw lastError;
  };

  const fetchToken = async () => {
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);
    const { data } = await api.post<{ access_token: string; token_type?: string }>(
      "/auth/token",
      body,
      {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      }
    );
    return data.access_token;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (isRegister && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await api.post("/auth/register", {
          email,
          password,
          role: registerRole,
        });
      }
      const token = await fetchTokenWithRetry();
      login(token);
      const r = parseRoleFromNewToken(token);
      navigate(r === "verifier" ? "/verify" : "/upload", { replace: true });
    } catch (err: unknown) {
      if (isTransientNetworkError(err)) {
        setError(
          "Backend is waking up or temporarily unreachable. Please wait a few seconds and try again."
        );
      } else {
        setError(formatApiError(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container flex min-h-[calc(100vh-4rem)] items-center justify-center py-12">
      <div className="animate-fade-up glass-card w-full max-w-md p-8">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <ShieldCheck className="h-6 w-6 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">
            {isRegister ? "Create Account" : "Sign in"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {isRegister
              ? "Choose whether you issue certificates or verify them."
              : "Institution accounts issue certificates; verifiers can sign in to track verification history."}
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div className="space-y-3">
              <span className="text-sm font-medium">Account type</span>
              <div className="grid gap-3">
                <label
                  className={cn(
                    "flex cursor-pointer gap-3 rounded-lg border p-4 transition-colors",
                    registerRole === "institution"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/30"
                  )}
                >
                  <input
                    type="radio"
                    name="role"
                    className="mt-1"
                    checked={registerRole === "institution"}
                    onChange={() => setRegisterRole("institution")}
                  />
                  <div>
                    <div className="flex items-center gap-2 font-semibold">
                      <Building2 className="h-4 w-4 text-primary" />
                      Institution
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Issue and manage academic certificates with QR codes.
                    </p>
                  </div>
                </label>
                <label
                  className={cn(
                    "flex cursor-pointer gap-3 rounded-lg border p-4 transition-colors",
                    registerRole === "verifier"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/30"
                  )}
                >
                  <input
                    type="radio"
                    name="role"
                    className="mt-1"
                    checked={registerRole === "verifier"}
                    onChange={() => setRegisterRole("verifier")}
                  />
                  <div>
                    <div className="flex items-center gap-2 font-semibold">
                      <UserCheck className="h-4 w-4 text-primary" />
                      Verifier
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Verify authenticity of certificates (optional login for history).
                    </p>
                  </div>
                </label>
              </div>
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@institution.edu"
              className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
            />
          </div>

          {isRegister && (
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                Confirm Password
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors active:scale-[0.98]"
          >
            {loading ? "Please wait..." : isRegister ? "Create Account" : "Login"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError("");
            }}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {isRegister
              ? "Already have an account? Sign in"
              : "Don't have an account? Register"}
          </button>
        </div>
      </div>
    </div>
  );
};

function parseRoleFromNewToken(token: string): UserRole | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json = decodeURIComponent(
      atob(padded)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    const payload = JSON.parse(json) as { role?: string };
    if (payload.role === "institution" || payload.role === "verifier") {
      return payload.role;
    }
    return null;
  } catch {
    return null;
  }
}

export default LoginPage;

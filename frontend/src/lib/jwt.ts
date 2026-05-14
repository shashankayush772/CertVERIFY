export type UserRole = "institution" | "verifier";

export function parseJwtPayload(token: string): Record<string, unknown> | null {
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
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getRoleFromToken(token: string | null): UserRole | null {
  if (!token) return null;
  const payload = parseJwtPayload(token);
  const r = payload?.role;
  if (r === "institution" || r === "verifier") return r;
  return null;
}

export function getEmailFromToken(token: string | null): string | null {
  if (!token) return null;
  const payload = parseJwtPayload(token);
  const email = payload?.email;
  return typeof email === "string" ? email : null;
}

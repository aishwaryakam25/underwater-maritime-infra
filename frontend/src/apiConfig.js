/**
 * Base URL for REST calls.
 * - CRA dev (`npm start`, port 3000): empty → same-origin `/api/...` proxied to backend (see package.json "proxy").
 * - Override: set REACT_APP_API_BASE_URL (CRA) or VITE_API_BASE_URL (Vite) to full origin, e.g. https://api.example.com
 */
export function getApiBaseUrl() {
  const react =
    typeof process !== "undefined" && process.env && process.env.REACT_APP_API_BASE_URL;
  if (react) return String(react).replace(/\/$/, "");

  let vite = "";
  try {
    if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
      vite = String(import.meta.env.VITE_API_BASE_URL);
    }
  } catch {
    /* ignore */
  }
  if (vite) return vite.replace(/\/$/, "");

  if (typeof window !== "undefined") {
    const port = window.location.port;
    if (port === "3000") return "";
  }
  return "http://localhost:8000";
}

/** Absolute or same-origin path for fetch(), e.g. apiUrl('/api/health') */
export function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  const base = getApiBaseUrl();
  if (!base) return p;
  return `${base.replace(/\/$/, "")}${p}`;
}

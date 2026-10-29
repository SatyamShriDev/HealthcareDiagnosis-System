const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "heartwise_token";

// Only the JWT is stored (sessionStorage: cleared when the tab closes). No passwords or health data.
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export class ApiError extends Error {
  constructor(message, status, fieldErrors = null) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function parseDetail(data, status) {
  const d = data && data.detail;
  if (typeof d === "string") return { message: d };
  if (Array.isArray(d)) { // pydantic validation errors
    const fieldErrors = {};
    d.forEach((e) => { const k = e.loc?.[e.loc.length - 1]; if (k) fieldErrors[k] = e.msg.replace(/^Value error, /, ""); });
    return { message: Object.values(fieldErrors)[0] || "Please check your input.", fieldErrors };
  }
  if (d && typeof d === "object") return { message: d.message || "Request failed.", fieldErrors: d.errors || null };
  return { message: `Request failed (${status}).` };
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = tokenStore.get();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) {
    if (res.status === 401 && auth && token) { tokenStore.clear(); onUnauthorized(); }
    const { message, fieldErrors } = parseDetail(data, res.status);
    throw new ApiError(message, res.status, fieldErrors);
  }
  return data;
}

export const api = {
  register: (b) => request("/api/auth/register", { method: "POST", body: b, auth: false }),
  login: (b) => request("/api/auth/login", { method: "POST", body: b, auth: false }),
  me: () => request("/api/auth/me"),
  features: () => request("/api/features", { auth: false }),
  modelInfo: () => request("/api/model-info", { auth: false }),
  predict: (inputs) => request("/api/predict", { method: "POST", body: { inputs } }),
  history: (skip = 0, limit = 10) => request(`/api/predictions/history?skip=${skip}&limit=${limit}`),
  prediction: (id) => request(`/api/predictions/${id}`),
  deletePrediction: (id) => request(`/api/predictions/${id}`, { method: "DELETE" }),
};

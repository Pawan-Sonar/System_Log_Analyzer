import axios from "axios";

const baseURL = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${baseURL}/api`,
  withCredentials: true,
  timeout: 30000,
});

// Attach bearer token (set after login) to every request.
// Falls back to cookies for local dev where withCredentials works.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function apiError(e, fallback = "Request failed") {
  return formatApiErrorDetail(e?.response?.data?.detail) || e?.message || fallback;
}

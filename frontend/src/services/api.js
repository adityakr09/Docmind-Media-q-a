import axios from "axios";

const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

const api = axios.create({ baseURL: BASE });

// Attach token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh });
          localStorage.setItem("access_token", data.access);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(err);
  }
);

// Auth
export const authAPI = {
  register: (data) => api.post("/auth/register/", data),
  login: async (data) => {
    const res = await api.post("/auth/login/", data);
    localStorage.setItem("access_token", res.data.access);
    localStorage.setItem("refresh_token", res.data.refresh);
    return res;
  },
  me: () => api.get("/auth/me/"),
  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
};

// Documents
export const documentsAPI = {
  list: () => api.get("/documents/"),
  upload: (formData, onProgress) =>
    api.post("/documents/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / e.total)),
    }),
  get: (id) => api.get(`/documents/${id}/`),
  delete: (id) => api.delete(`/documents/${id}/`),
  summary: (id) => api.get(`/documents/${id}/summary/`),
};

// Chat
export const chatAPI = {
  ask: (docId, question) => api.post(`/documents/${docId}/ask/`, { question }),
  history: (docId) => api.get(`/documents/${docId}/chat/`),
  clear: (docId) => api.delete(`/documents/${docId}/chat/`),
};

// Timestamps
export const timestampAPI = {
  search: (docId, topic) =>
    api.get(`/documents/${docId}/timestamps/`, { params: topic ? { topic } : {} }),
};

export default api;

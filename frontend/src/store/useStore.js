import { create } from "zustand";
import { authAPI, documentsAPI } from "../services/api";

const useStore = create((set, get) => ({
  // Auth
  user: null,
  authLoading: false,
  authError: null,

  login: async (username, password) => {
    set({ authLoading: true, authError: null });
    try {
      await authAPI.login({ username, password });
      const { data } = await authAPI.me();
      set({ user: data, authLoading: false });
      return true;
    } catch (err) {
      set({ authError: err.response?.data?.detail || "Login failed", authLoading: false });
      return false;
    }
  },

  register: async (username, email, password) => {
    set({ authLoading: true, authError: null });
    try {
      await authAPI.register({ username, email, password });
      return await get().login(username, password);
    } catch (err) {
      const msg =
        err.response?.data?.username?.[0] ||
        err.response?.data?.password?.[0] ||
        "Registration failed";
      set({ authError: msg, authLoading: false });
      return false;
    }
  },

  logout: () => {
    authAPI.logout();
    set({ user: null, documents: [], activeDocument: null, messages: [] });
  },

  initAuth: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    try {
      const { data } = await authAPI.me();
      set({ user: data });
    } catch {
      localStorage.clear();
    }
  },

  // Documents
  documents: [],
  documentsLoading: false,
  activeDocument: null,
  uploadProgress: 0,

  fetchDocuments: async () => {
    set({ documentsLoading: true });
    try {
      const { data } = await documentsAPI.list();
      set({ documents: data, documentsLoading: false });
    } catch {
      set({ documentsLoading: false });
    }
  },

  uploadDocument: async (file, title, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title || file.name);
    try {
      const { data } = await documentsAPI.upload(formData, (p) => {
        set({ uploadProgress: p });
        onProgress?.(p);
      });
      set((state) => ({ documents: [data, ...state.documents], uploadProgress: 0 }));
      return data;
    } catch (err) {
      set({ uploadProgress: 0 });
      throw err;
    }
  },

  deleteDocument: async (id) => {
    await documentsAPI.delete(id);
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== id),
      activeDocument: state.activeDocument?.id === id ? null : state.activeDocument,
    }));
  },

  setActiveDocument: (doc) => set({ activeDocument: doc, messages: [] }),

  refreshDocument: async (id) => {
    const { data } = await documentsAPI.get(id);
    set((state) => ({
      documents: state.documents.map((d) => (d.id === id ? data : d)),
      activeDocument: state.activeDocument?.id === id ? data : state.activeDocument,
    }));
    return data;
  },

  // Chat
  messages: [],
  chatLoading: false,

  fetchHistory: async (docId) => {
    const { data } = await import("../services/api").then((m) => m.chatAPI.history(docId));
    set({ messages: data });
  },

  askQuestion: async (docId, question) => {
    const userMsg = { id: Date.now(), role: "user", content: question };
    set((state) => ({ messages: [...state.messages, userMsg], chatLoading: true }));
    try {
      const { chatAPI } = await import("../services/api");
      const { data } = await chatAPI.ask(docId, question);
      set((state) => ({ messages: [...state.messages, data], chatLoading: false }));
      return data;
    } catch (err) {
      set({ chatLoading: false });
      throw err;
    }
  },

  clearChat: async (docId) => {
    const { chatAPI } = await import("../services/api");
    await chatAPI.clear(docId);
    set({ messages: [] });
  },
}));

export default useStore;

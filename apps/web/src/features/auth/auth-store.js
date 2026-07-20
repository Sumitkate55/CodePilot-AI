import { create } from "zustand";

import { clearAccessToken } from "./auth-session";
import { login, logout, refreshSession, register } from "./auth-service";

export const useAuthStore = create((set) => ({
  status: "checking",
  user: null,
  initializeSession: async () => {
    try {
      const session = await refreshSession();
      set({ status: "authenticated", user: session.user });
    } catch {
      clearAccessToken();
      set({ status: "anonymous", user: null });
    }
  },
  signIn: async (credentials) => {
    const session = await login(credentials);
    set({ status: "authenticated", user: session.user });
    return session.user;
  },
  signUp: async (account) => {
    const session = await register(account);
    set({ status: "authenticated", user: session.user });
    return session.user;
  },
  signOut: async () => {
    try {
      await logout();
    } finally {
      set({ status: "anonymous", user: null });
    }
  },
}));

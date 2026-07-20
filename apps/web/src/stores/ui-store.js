import { create } from "zustand";

const isTheme = (value) => ["light", "dark", "system"].includes(value);

const savedTheme = typeof window === "undefined" ? null : window.localStorage.getItem("codepilot-theme");

export const useUiStore = create((set) => ({
  sidebarOpen: false,
  theme: isTheme(savedTheme) ? savedTheme : "system",
  openSidebar: () => set({ sidebarOpen: true }),
  closeSidebar: () => set({ sidebarOpen: false }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => {
    if (!isTheme(theme)) {
      return;
    }
    window.localStorage.setItem("codepilot-theme", theme);
    set({ theme });
  },
}));

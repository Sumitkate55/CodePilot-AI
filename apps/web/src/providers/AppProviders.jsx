import { useEffect, useMemo } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppErrorBoundary } from "@/components/common/AppErrorBoundary";
import { useUiStore } from "@/stores/ui-store";

function ThemeSynchronizer({ children }) {
  const theme = useUiStore((state) => state.theme);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = () => {
      const shouldUseDark = theme === "dark" || (theme === "system" && mediaQuery.matches);
      document.documentElement.classList.toggle("dark", shouldUseDark);
    };

    applyTheme();
    mediaQuery.addEventListener("change", applyTheme);
    return () => mediaQuery.removeEventListener("change", applyTheme);
  }, [theme]);

  return children;
}

export function AppProviders({ children }) {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
            staleTime: 30_000,
          },
        },
      }),
    [],
  );

  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeSynchronizer>{children}</ThemeSynchronizer>
      </QueryClientProvider>
    </AppErrorBoundary>
  );
}

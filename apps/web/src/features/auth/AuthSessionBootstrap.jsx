import { useEffect } from "react";

import { LoadingScreen } from "@/components/common/LoadingScreen";

import { useAuthStore } from "./auth-store";

export function AuthSessionBootstrap({ children }) {
  const status = useAuthStore((state) => state.status);
  const initializeSession = useAuthStore((state) => state.initializeSession);

  useEffect(() => {
    void initializeSession();
  }, [initializeSession]);

  if (status === "checking") {
    return <LoadingScreen label="Restoring your secure session" />;
  }

  return children;
}

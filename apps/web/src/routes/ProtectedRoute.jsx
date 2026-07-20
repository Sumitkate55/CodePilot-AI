import { Navigate, Outlet, useLocation } from "react-router-dom";

import { LoadingScreen } from "@/components/common/LoadingScreen";
import { useAuthStore } from "@/features/auth/auth-store";

export function ProtectedRoute() {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();

  if (status === "checking") {
    return <LoadingScreen label="Checking your secure session" />;
  }

  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

import { RouterProvider } from "react-router-dom";

import { AppProviders } from "@/providers/AppProviders";
import { router } from "@/routes/router";
import { AuthSessionBootstrap } from "@/features/auth/AuthSessionBootstrap";

export function App() {
  return (
    <AppProviders>
      <AuthSessionBootstrap>
        <RouterProvider router={router} />
      </AuthSessionBootstrap>
    </AppProviders>
  );
}

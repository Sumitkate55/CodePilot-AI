import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/pages/layouts/AppLayout";
import { AuthLayout } from "@/pages/layouts/AuthLayout";
import { PublicLayout } from "@/pages/layouts/PublicLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { RepositoryDetailPage } from "@/pages/RepositoryDetailPage";
import { RepositoryUploadPage } from "@/pages/RepositoryUploadPage";
import { RouteErrorPage } from "@/pages/RouteErrorPage";
import { WelcomePage } from "@/pages/WelcomePage";

import { ProtectedRoute } from "./ProtectedRoute";

export const router = createBrowserRouter([
  {
    path: "/",
    errorElement: <RouteErrorPage />,
    children: [
      {
        element: <PublicLayout />,
        children: [
          { index: true, element: <Navigate to="/welcome" replace /> },
          { path: "welcome", element: <WelcomePage /> },
        ],
      },
      {
        element: <AuthLayout />,
        children: [
          { path: "login", element: <LoginPage /> },
          { path: "register", element: <RegisterPage /> },
        ],
      },
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <AppLayout />,
            children: [
              { path: "dashboard", element: <DashboardPage /> },
              { path: "repositories/new", element: <RepositoryUploadPage /> },
              { path: "repositories/:repositoryId", element: <RepositoryDetailPage /> },
            ],
          },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

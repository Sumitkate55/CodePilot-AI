import { clearAccessToken, setAccessToken } from "@/features/auth/auth-session";
import { apiClient, configureAccessTokenRefresh } from "@/services/api-client";

function toSession(payload) {
  setAccessToken(payload.access_token);
  return {
    accessToken: payload.access_token,
    expiresIn: payload.expires_in,
    user: payload.user,
  };
}

export async function login(credentials) {
  const { data } = await apiClient.post("/auth/login", credentials);
  return toSession(data);
}

export async function register(account) {
  const { data } = await apiClient.post("/auth/register", account);
  return toSession(data);
}

export async function refreshSession() {
  const { data } = await apiClient.post("/auth/refresh");
  return toSession(data);
}

export async function logout() {
  try {
    await apiClient.post("/auth/logout");
  } finally {
    clearAccessToken();
  }
}

configureAccessTokenRefresh(async () => {
  const session = await refreshSession();
  return session.accessToken;
});

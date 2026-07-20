import axios from "axios";

import { getAccessToken } from "@/features/auth/auth-session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const API_TIMEOUT_MS = 300_000;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  // Local models can take longer than a cloud API, especially while loading into memory.
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});

let refreshAccessTokenHandler = null;
let pendingRefresh = null;

export function configureAccessTokenRefresh(handler) {
  refreshAccessTokenHandler = handler;
}

export class ApiError extends Error {
  constructor(message, { code = "request_failed", status = 0, requestId = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

apiClient.interceptors.request.use((config) => {
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const isAuthenticationRequest = request?.url?.includes("/auth/");
    if (
      error.response?.status === 401 &&
      request &&
      !request._retriedAfterRefresh &&
      !isAuthenticationRequest &&
      refreshAccessTokenHandler
    ) {
      request._retriedAfterRefresh = true;
      try {
        pendingRefresh ??= refreshAccessTokenHandler().finally(() => {
          pendingRefresh = null;
        });
        const accessToken = await pendingRefresh;
        request.headers.Authorization = `Bearer ${accessToken}`;
        return apiClient(request);
      } catch {
        return Promise.reject(
          new ApiError("Your session has expired. Please sign in again.", {
            code: "session_expired",
            status: 401,
          }),
        );
      }
    }
    const payload = error.response?.data?.error;
    return Promise.reject(
      new ApiError(payload?.message ?? "We could not complete that request.", {
        code: payload?.code,
        status: error.response?.status,
        requestId: payload?.request_id,
      }),
    );
  },
);

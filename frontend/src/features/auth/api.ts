import axios from "axios";

import { api } from "../../lib/api";
import { getDeviceId } from "../../lib/device";

export interface AuthUser {
  id: string;
  username: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
  status: string;
}

export const authApi = {
  /** Prime the CSRF cookie before a write request. */
  async csrf(): Promise<void> {
    await api.get("/auth/csrf/");
  },
  async login(username: string, password: string, role: string): Promise<AuthUser> {
    try {
      const { data } = await api.post<AuthUser>("/auth/login/", {
        username,
        password,
        role,
        device_id: getDeviceId(),
      });
      return data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        if (detail) throw new Error(detail);
      }
      throw new Error("Invalid credentials for this portal.");
    }
  },
  async logout(): Promise<void> {
    await api.post("/auth/logout/");
  },
  /** Current user, or null if not signed in. */
  async me(): Promise<AuthUser | null> {
    try {
      const { data } = await api.get<AuthUser>("/auth/me/");
      return data;
    } catch {
      return null;
    }
  },
};

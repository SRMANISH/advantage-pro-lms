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

/** Thrown when the password was correct but a staff account also needs its TOTP code. */
export class TotpRequiredError extends Error {}

export const authApi = {
  /** Prime the CSRF cookie before a write request. */
  async csrf(): Promise<void> {
    await api.get("/auth/csrf/");
  },
  async login(
    username: string,
    password: string,
    role?: string,
    totpCode?: string,
  ): Promise<AuthUser> {
    try {
      const { data } = await api.post<AuthUser>("/auth/login/", {
        username,
        password,
        // Omitted on the unified sign-in — the backend routes by the account's role.
        ...(role ? { role } : {}),
        ...(totpCode ? { totp_code: totpCode } : {}),
        device_id: await getDeviceId(),
      });
      return data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const body = err.response?.data as { detail?: string; totp_required?: boolean } | undefined;
        if (body?.totp_required) throw new TotpRequiredError(body.detail ?? "Enter your code.");
        if (body?.detail) throw new Error(body.detail);
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

import { api } from "../../lib/api";

export interface TOTPEnrollment {
  secret: string;
  otpauth_url: string;
}

export const totpApi = {
  async status(): Promise<{ enabled: boolean }> {
    return (await api.get<{ enabled: boolean }>("/auth/totp/status/")).data;
  },
  async enroll(): Promise<TOTPEnrollment> {
    return (await api.post<TOTPEnrollment>("/auth/totp/enroll/")).data;
  },
  async confirm(code: string): Promise<void> {
    await api.post("/auth/totp/confirm/", { code });
  },
  async disable(password: string): Promise<void> {
    await api.post("/auth/totp/disable/", { password });
  },
};

import { api } from "../../lib/api";

interface StartResult {
  ok: boolean;
  token: string;
  email: string;
  dev_code?: string;
}

interface StepResult {
  ok: boolean;
  phone?: string;
  dev_code?: string;
}

export const passwordApi = {
  async forgot(identifier: string): Promise<StartResult> {
    return (await api.post<StartResult>("/auth/password/forgot/", { identifier })).data;
  },
  async verifyEmail(token: string, code: string): Promise<StepResult> {
    return (await api.post<StepResult>("/auth/password/verify-email/", { token, code })).data;
  },
  async verifyPhone(token: string, code: string): Promise<StepResult> {
    return (await api.post<StepResult>("/auth/password/verify-phone/", { token, code })).data;
  },
  async reset(token: string, password: string): Promise<void> {
    await api.post("/auth/password/reset/", { token, password });
  },
  async resend(token: string): Promise<StepResult> {
    return (await api.post<StepResult>("/auth/password/resend/", { token })).data;
  },
  async change(oldPassword: string, newPassword: string): Promise<void> {
    await api.post("/auth/password/change/", {
      old_password: oldPassword,
      new_password: newPassword,
    });
  },
};

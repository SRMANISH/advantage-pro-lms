import axios from "axios";

import { api } from "../../lib/api";

export interface StepResult {
  ok?: boolean;
  email?: string;
  phone?: string;
  dev_code?: string;
  detail?: string;
}

async function call(url: string, body: Record<string, string>): Promise<StepResult> {
  try {
    const { data } = await api.post<StepResult>(url, body);
    return data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      return err.response.data as StepResult;
    }
    throw err;
  }
}

export const setupApi = {
  start: (token: string) => call("/auth/setup/start/", { token }),
  verifyEmail: (token: string, code: string) => call("/auth/setup/verify-email/", { token, code }),
  verifyPhone: (token: string, code: string) => call("/auth/setup/verify-phone/", { token, code }),
  complete: (token: string, password: string) =>
    call("/auth/setup/complete/", { token, password }),
};

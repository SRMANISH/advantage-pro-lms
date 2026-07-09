import { api } from "../../lib/api";

export interface WelcomePrompt {
  enrollment: string;
  batch_code: string;
  batch_name: string;
  address: string;
}

export interface GoodiesRow {
  enrollment: string;
  registration_number: string;
  student_name: string;
  batch_code: string;
  address: string;
  address_confirmed: boolean;
  goodies_received: boolean;
  goodies_sent: boolean;
}

export const welcomeApi = {
  async pending(): Promise<WelcomePrompt[]> {
    return (await api.get<WelcomePrompt[]>("/welcome/me/")).data;
  },
  async submit(payload: {
    enrollment: string;
    address_on_file: boolean;
    goodies_received: boolean;
    address?: string;
  }): Promise<void> {
    await api.post("/welcome/submit/", payload);
  },
  async register(): Promise<GoodiesRow[]> {
    return (await api.get<GoodiesRow[]>("/welcome/register/")).data;
  },
  async setGoodiesSent(enrollment: string, sent: boolean): Promise<void> {
    await api.post("/welcome/goodies/", { enrollment, sent });
  },
};

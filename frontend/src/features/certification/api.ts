import { api } from "../../lib/api";

export interface CertRow {
  enrollment: string;
  batch_code: string;
  batch_name: string;
  certificate_id: string | null;
  certified: boolean;
}

export const certificationApi = {
  async me(): Promise<CertRow[]> {
    return (await api.get<CertRow[]>("/certification/me/")).data;
  },
  async submit(enrollment: string, certificateId: string): Promise<void> {
    await api.post("/certification/submit/", { enrollment, certificate_id: certificateId });
  },
  async remind(): Promise<{ reminded: number }> {
    return (await api.post("/certification/remind/")).data;
  },
};

import { api } from "../../lib/api";

export interface CertRow {
  enrollment: string;
  batch_code: string;
  batch_name: string;
  certificate_id: string | null;
  certified: boolean;
}

export type CertFollowUpStatus = "pending" | "contacted" | "received" | "escalated";

export const CERT_FOLLOW_UP_STATUSES: { value: CertFollowUpStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "contacted", label: "Contacted" },
  { value: "received", label: "Received" },
  { value: "escalated", label: "Escalated" },
];

export interface CertFollowUpRow {
  enrollment: string;
  registration_number: string;
  student_name: string;
  batch_code: string;
  certified: boolean;
  certificate_id: string | null;
  follow_up_status: CertFollowUpStatus;
  reminder_count: number;
  last_reminder_at: string | null;
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
  async followUpList(): Promise<CertFollowUpRow[]> {
    return (await api.get<CertFollowUpRow[]>("/certification/follow-up/")).data;
  },
  async setFollowUpStatus(
    enrollment: string,
    status: CertFollowUpStatus,
    note?: string,
  ): Promise<void> {
    await api.post("/certification/follow-up/status/", { enrollment, status, note: note ?? "" });
  },
};

import { api } from "../../lib/api";

export interface FeedbackRow {
  id: string;
  student_name: string;
  registration_number: string;
  batch_code: string;
  course_name: string;
  subject: string;
  message: string;
  created_at: string;
}

export const feedbackApi = {
  async send(payload: { subject: string; message: string }): Promise<void> {
    await api.post("/feedback/", payload);
  },
  async inbox(): Promise<FeedbackRow[]> {
    return (await api.get<FeedbackRow[]>("/feedback/inbox/")).data;
  },
};

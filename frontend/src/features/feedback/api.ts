import { api, fetchPage, type Page } from "../../lib/api";

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
  /** Server-paginated: the inbox grows with every submission. */
  async inbox(params: Record<string, unknown> = {}): Promise<Page<FeedbackRow>> {
    return fetchPage<FeedbackRow>("/feedback/inbox/", params);
  },
};

import { api } from "../../lib/api";

export interface EngagementStudent {
  registration_number: string;
  student_name: string;
  status: string;
  reminder_count: number;
}

export interface LinkedInReport {
  confirmed: number;
  pending: number;
  students: EngagementStudent[];
}

export interface GoogleReport {
  submitted: number;
  pending: number;
  students: EngagementStudent[];
}

export interface NextPlanRow {
  registration_number: string;
  student_name: string;
  batch_code: string | null;
  planning_another_course: boolean;
  interested_course: string;
  expected_timing: string;
  goal: string;
  preferred_contact_time: string;
  notes: string;
  submitted_at: string;
}

export interface EngagementMe {
  linkedin: { status: string; show: boolean };
  google_review: { status: string | null; show: boolean };
  next_plan: { show: boolean };
}

export interface NextPlanInput {
  planning_another_course: boolean;
  interested_course: string;
  expected_timing: string;
  goal: string;
  preferred_contact_time: string;
}

export const engagementApi = {
  async me(): Promise<EngagementMe> {
    return (await api.get<EngagementMe>("/engagement/me/")).data;
  },
  async linkedinAction(action: "opened" | "confirmed" | "skipped"): Promise<void> {
    await api.post("/engagement/linkedin/", { action });
  },
  async googleReviewAction(action: "opened" | "submitted" | "skipped"): Promise<void> {
    await api.post("/engagement/google-review/", { action });
  },
  async submitNextPlan(body: NextPlanInput): Promise<void> {
    await api.post("/engagement/next-plan/", body);
  },
  async linkedinReport(batchId?: string): Promise<LinkedInReport> {
    const q = batchId ? `?batch=${batchId}` : "";
    return (await api.get<LinkedInReport>(`/engagement/reports/linkedin/${q}`)).data;
  },
  async googleReport(batchId?: string): Promise<GoogleReport> {
    const q = batchId ? `?batch=${batchId}` : "";
    return (await api.get<GoogleReport>(`/engagement/reports/google-review/${q}`)).data;
  },
  async nextPlans(batchId?: string): Promise<NextPlanRow[]> {
    const q = batchId ? `?batch=${batchId}` : "";
    return (await api.get<NextPlanRow[]>(`/engagement/next-plans/${q}`)).data;
  },
};

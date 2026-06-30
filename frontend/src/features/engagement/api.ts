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

export const engagementApi = {
  async linkedinReport(): Promise<LinkedInReport> {
    return (await api.get<LinkedInReport>("/engagement/reports/linkedin/")).data;
  },
  async googleReport(): Promise<GoogleReport> {
    return (await api.get<GoogleReport>("/engagement/reports/google-review/")).data;
  },
  async nextPlans(): Promise<NextPlanRow[]> {
    return (await api.get<NextPlanRow[]>("/engagement/next-plans/")).data;
  },
};

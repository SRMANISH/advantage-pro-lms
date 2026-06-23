import { api } from "../../lib/api";

export interface DashboardBatch {
  id: string;
  code: string;
  name: string;
  course: string;
  state: string;
  start_date?: string;
  end_date?: string;
  faculty?: string[];
  student_count?: number;
}

export interface DashboardData {
  role: string;
  batches?: DashboardBatch[];
  totals?: Record<string, number>;
}

export const dashboardApi = {
  async get(): Promise<DashboardData> {
    return (await api.get<DashboardData>("/dashboard/")).data;
  },
};

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

// Index signature lets these pass straight into the Recharts `data` prop.
export interface TrendPoint {
  label: string;
  value: number;
  [key: string]: string | number;
}

export interface NamedValue {
  name: string;
  value: number;
  [key: string]: string | number;
}

export interface UpNextItem {
  title: string;
  batch_code: string;
  scheduled_at: string;
}

export interface DashboardData {
  role: string;
  batches?: DashboardBatch[];
  totals?: Record<string, number>;
  kpis?: Record<string, number>;
  videos?: { completed: number; total: number };
  trend?: TrendPoint[];
  up_next?: UpNextItem[];
  attention?: Record<string, number>;
  batch_states?: NamedValue[];
  forum_status?: NamedValue[];
}

export const dashboardApi = {
  async get(): Promise<DashboardData> {
    return (await api.get<DashboardData>("/dashboard/")).data;
  },
};

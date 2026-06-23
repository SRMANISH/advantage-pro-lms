import { api } from "../../lib/api";

export interface PerfMetrics {
  test_pct: number;
  task_pct: number;
  video_pct: number;
  attendance_pct: number;
  overall: number;
}

export interface MyPerfRow extends PerfMetrics {
  batch: string;
  batch_name: string;
  size: number;
  rank: number;
}

export interface BoardRow extends PerfMetrics {
  student: string;
  student_name: string;
  registration_number: string;
  rank: number;
}

export const performanceApi = {
  async me(): Promise<MyPerfRow[]> {
    return (await api.get<MyPerfRow[]>("/performance/me/")).data;
  },
  async batch(batchId: string): Promise<BoardRow[]> {
    return (await api.get<BoardRow[]>(`/performance/?batch=${batchId}`)).data;
  },
};

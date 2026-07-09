import { api } from "../../lib/api";

export interface Course {
  id: string;
  code: string;
  name: string;
  description?: string;
  duration?: string;
  fees?: string | null;
}

export interface FacultyBrief {
  id: string;
  username: string;
  full_name: string;
  skills?: string;
  certifications?: string;
}

export type BatchState = "draft" | "active" | "completed";
export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";
export const WEEKDAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

export interface Batch {
  id: string;
  code: string;
  name: string;
  course: string;
  course_detail: Course;
  start_date: string;
  end_date: string;
  class_days: Weekday[];
  class_start_time: string | null;
  class_end_time: string | null;
  state: BatchState;
  faculty: string[];
  faculty_detail: FacultyBrief[];
  primary_faculty: string | null;
  primary_faculty_detail: FacultyBrief | null;
  created_at: string;
}

export interface NewBatch {
  code: string;
  name: string;
  course: string;
  start_date: string;
  end_date: string;
  class_days: Weekday[];
  class_start_time: string;
  class_end_time: string;
}

export const batchesApi = {
  async listCourses(): Promise<Course[]> {
    return (await api.get<Course[]>("/courses/")).data;
  },
  async createCourse(payload: {
    code: string;
    name: string;
    description?: string;
    duration?: string;
    fees?: string;
  }): Promise<Course> {
    return (await api.post<Course>("/courses/", payload)).data;
  },
  async listBatches(): Promise<Batch[]> {
    return (await api.get<Batch[]>("/batches/")).data;
  },
  async createBatch(payload: NewBatch): Promise<Batch> {
    return (await api.post<Batch>("/batches/", payload)).data;
  },
  async transition(id: string, to_state: BatchState): Promise<Batch> {
    return (await api.post<Batch>(`/batches/${id}/transition/`, { to_state })).data;
  },
  async assignFaculty(
    id: string,
    payload: { primary_faculty?: string; faculty_ids?: string[] },
  ): Promise<Batch> {
    return (await api.post<Batch>(`/batches/${id}/assign-faculty/`, payload)).data;
  },
  async listFaculty(): Promise<FacultyBrief[]> {
    return (await api.get<FacultyBrief[]>("/faculty/")).data;
  },
};

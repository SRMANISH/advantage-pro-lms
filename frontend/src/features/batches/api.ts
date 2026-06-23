import { api } from "../../lib/api";

export interface Course {
  id: string;
  code: string;
  name: string;
  description?: string;
}

export interface FacultyBrief {
  id: string;
  username: string;
  full_name: string;
}

export type BatchState = "draft" | "active" | "completed";

export interface Batch {
  id: string;
  code: string;
  name: string;
  course: string;
  course_detail: Course;
  start_date: string;
  end_date: string;
  state: BatchState;
  faculty: string[];
  faculty_detail: FacultyBrief[];
  created_at: string;
}

export interface NewBatch {
  code: string;
  name: string;
  course: string;
  start_date: string;
  end_date: string;
}

export const batchesApi = {
  async listCourses(): Promise<Course[]> {
    return (await api.get<Course[]>("/courses/")).data;
  },
  async createCourse(payload: { code: string; name: string }): Promise<Course> {
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
  async assignFaculty(id: string, facultyIds: string[]): Promise<Batch> {
    return (await api.post<Batch>(`/batches/${id}/assign-faculty/`, { faculty_ids: facultyIds }))
      .data;
  },
  async listFaculty(): Promise<FacultyBrief[]> {
    return (await api.get<FacultyBrief[]>("/faculty/")).data;
  },
};

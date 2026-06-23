import { api } from "../../lib/api";

export interface MySubmission {
  submitted_at: string;
  is_late: boolean;
  score: number | null;
  feedback: string;
  text: string;
  has_file: boolean;
}

export interface TaskItem {
  id: string;
  batch: string;
  title: string;
  description: string;
  deadline: string | null;
  submission_count?: number;
  my_submission: MySubmission | null;
  is_overdue: boolean;
  created_at: string;
}

export interface Submission {
  id: string;
  student_name: string;
  registration_number: string;
  text: string;
  file_url: string;
  is_late: boolean;
  score: number | null;
  feedback: string;
  submitted_at: string;
}

export interface NewTask {
  batch: string;
  title: string;
  description?: string;
  deadline?: string;
}

export const tasksApi = {
  async list(batchId?: string): Promise<TaskItem[]> {
    return (await api.get<TaskItem[]>(`/tasks/${batchId ? `?batch=${batchId}` : ""}`)).data;
  },
  async create(payload: NewTask): Promise<TaskItem> {
    return (await api.post<TaskItem>("/tasks/", payload)).data;
  },
  async submit(id: string, body: { text?: string; file?: File | null }): Promise<void> {
    if (body.file) {
      const form = new FormData();
      form.append("text", body.text ?? "");
      form.append("file", body.file);
      await api.post(`/tasks/${id}/submit/`, form);
    } else {
      await api.post(`/tasks/${id}/submit/`, { text: body.text ?? "" });
    }
  },
  async submissions(id: string): Promise<Submission[]> {
    return (await api.get<Submission[]>(`/tasks/${id}/submissions/`)).data;
  },
  async grade(submissionId: string, body: { score: number; feedback: string }): Promise<void> {
    await api.post(`/task-submissions/${submissionId}/grade/`, body);
  },
};

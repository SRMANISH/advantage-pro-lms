import { api } from "../../lib/api";

export type TestKind = "mcq" | "file" | "colab";

export interface Attempt {
  score: number;
  total: number;
  graded: boolean;
  feedback: string;
  link: string;
  has_file: boolean;
}

export interface TestListItem {
  id: string;
  batch: string;
  title: string;
  kind: TestKind;
  max_score: number;
  open_at: string | null;
  close_at: string | null;
  question_count?: number;
  attempt_count?: number;
  is_open: boolean;
  my_attempt: Attempt | null;
}

export interface TestAttemptRow {
  id: string;
  student_name: string;
  registration_number: string;
  score: number;
  total: number;
  graded: boolean;
  feedback: string;
  link: string;
  file_url: string;
  submitted_at: string;
}

export interface TakeChoice {
  id: string;
  text: string;
}

export interface TakeQuestion {
  id: string;
  text: string;
  choices: TakeChoice[];
}

export interface TestDetail {
  id: string;
  title: string;
  kind: TestKind;
  instructions: string;
  max_score: number;
  is_open: boolean;
  my_attempt: Attempt | null;
  questions: TakeQuestion[];
}

export interface NewChoice {
  text: string;
  is_correct: boolean;
}

export interface NewQuestion {
  text: string;
  choices: NewChoice[];
}

export interface NewTest {
  batch: string;
  title: string;
  kind: TestKind;
  instructions?: string;
  max_score?: number;
  open_at?: string;
  close_at?: string;
  questions: NewQuestion[];
}

export const assessmentsApi = {
  async list(batchId?: string): Promise<TestListItem[]> {
    return (await api.get<TestListItem[]>(`/tests/${batchId ? `?batch=${batchId}` : ""}`)).data;
  },
  async get(id: string): Promise<TestDetail> {
    return (await api.get<TestDetail>(`/tests/${id}/`)).data;
  },
  async create(payload: NewTest): Promise<TestListItem> {
    return (await api.post<TestListItem>("/tests/", payload)).data;
  },
  async submit(
    id: string,
    answers: { question: string; choice: string }[],
  ): Promise<Attempt> {
    return (await api.post<Attempt>(`/tests/${id}/submit/`, { answers })).data;
  },
  /** File/Colab submission: an uploaded file or a notebook link. */
  async submitArtefact(id: string, body: { file?: File | null; link?: string }): Promise<void> {
    if (body.file) {
      const form = new FormData();
      form.append("file", body.file);
      if (body.link) form.append("link", body.link);
      await api.post(`/tests/${id}/submit/`, form);
      return;
    }
    await api.post(`/tests/${id}/submit/`, { link: body.link ?? "" });
  },
  async attempts(id: string): Promise<TestAttemptRow[]> {
    return (await api.get<TestAttemptRow[]>(`/tests/${id}/attempts/`)).data;
  },
  async gradeAttempt(
    attemptId: string,
    body: { score: number; feedback?: string },
  ): Promise<void> {
    await api.post(`/test-attempts/${attemptId}/grade/`, body);
  },
};

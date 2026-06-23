import { api } from "../../lib/api";

export interface Attempt {
  score: number;
  total: number;
}

export interface TestListItem {
  id: string;
  batch: string;
  title: string;
  open_at: string | null;
  close_at: string | null;
  question_count?: number;
  attempt_count?: number;
  is_open: boolean;
  my_attempt: Attempt | null;
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
};

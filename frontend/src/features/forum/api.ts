import { api, unwrap, type Paginated } from "../../lib/api";

export interface ReplyItem {
  id: string;
  author_name: string;
  body: string;
  created_at: string;
}

export type ThreadStatus = "open" | "answered" | "resolved" | "escalated";

export interface ThreadItem {
  id: string;
  batch: string;
  batch_code: string;
  title: string;
  body: string;
  resolved: boolean;
  status: ThreadStatus;
  author_name: string;
  reply_count: number;
  created_at: string;
}

export interface ThreadDetail extends ThreadItem {
  replies: ReplyItem[];
}

export interface ForumBatch {
  id: string;
  code: string;
  name: string;
}

export interface MonitorThread {
  id: string;
  title: string;
  batch_code: string;
  author_name: string;
  status: ThreadStatus;
  hours_waiting: number;
  overdue: boolean;
  faculty_pending: boolean;
  created_at: string;
}

export interface MonitorCounts {
  open: number;
  answered: number;
  escalated: number;
  resolved: number;
  answered_by_ts: number;
}

export interface MonitorResult {
  window_hours: number;
  threads: MonitorThread[];
  counts: MonitorCounts;
}

export const forumApi = {
  async list(q?: string): Promise<ThreadItem[]> {
    const { data } = await api.get<ThreadItem[] | Paginated<ThreadItem>>("/threads/", {
      params: { page_size: 100, ...(q ? { q } : {}) },
    });
    return unwrap(data);
  },
  async get(id: string): Promise<ThreadDetail> {
    return (await api.get<ThreadDetail>(`/threads/${id}/`)).data;
  },
  async create(payload: { batch: string; title: string; body: string }): Promise<ThreadItem> {
    return (await api.post<ThreadItem>("/threads/", payload)).data;
  },
  async reply(id: string, body: string): Promise<ThreadDetail> {
    return (await api.post<ThreadDetail>(`/threads/${id}/reply/`, { body })).data;
  },
  async resolve(id: string): Promise<void> {
    await api.post(`/threads/${id}/resolve/`);
  },
  async escalate(id: string): Promise<void> {
    await api.post(`/threads/${id}/escalate/`);
  },
  async batches(): Promise<ForumBatch[]> {
    return (await api.get<ForumBatch[]>("/forum/batches/")).data;
  },
  async monitor(): Promise<MonitorResult> {
    return (await api.get<MonitorResult>("/forum/monitor/")).data;
  },
  async remind(id: string): Promise<void> {
    await api.post(`/threads/${id}/remind/`);
  },
};

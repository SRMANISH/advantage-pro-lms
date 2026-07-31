import { api, fetchPage, type Page } from "../../lib/api";

export interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  download_url: string;
  created_at: string;
}

export interface ReplyItem {
  id: string;
  author_name: string;
  body: string;
  attachments: Attachment[];
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
  /** Whole hours an open doubt has waited; the 3h SLA applies to faculty + tech support. */
  hours_waiting: number;
  overdue: boolean;
  created_at: string;
}

export interface ThreadDetail extends ThreadItem {
  attachments: Attachment[];
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

/** Paginated envelope: `results` is the current page of unanswered threads, while
 *  `counts` and `window_hours` describe the whole dataset. */
export interface MonitorResult {
  count: number;
  results: MonitorThread[];
  window_hours: number;
  counts: MonitorCounts;
}

export const forumApi = {
  /** Server-paginated. Previously fetched page_size:100 and rendered the lot, so thread 101
   *  was silently invisible with nothing telling the user. */
  async list(params: Record<string, unknown> = {}): Promise<Page<ThreadItem>> {
    return fetchPage<ThreadItem>("/threads/", params);
  },
  async get(id: string): Promise<ThreadDetail> {
    return (await api.get<ThreadDetail>(`/threads/${id}/`)).data;
  },
  async create(payload: {
    batch: string;
    title: string;
    body: string;
    file?: File | null;
  }): Promise<ThreadItem> {
    if (payload.file) {
      const form = new FormData();
      form.append("batch", payload.batch);
      form.append("title", payload.title);
      form.append("body", payload.body);
      form.append("file", payload.file);
      return (await api.post<ThreadItem>("/threads/", form)).data;
    }
    return (await api.post<ThreadItem>("/threads/", payload)).data;
  },
  async reply(id: string, body: string, file?: File | null): Promise<ThreadDetail> {
    if (file) {
      const form = new FormData();
      form.append("body", body);
      form.append("file", file);
      return (await api.post<ThreadDetail>(`/threads/${id}/reply/`, form)).data;
    }
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
  async monitor(params: Record<string, unknown> = {}): Promise<MonitorResult> {
    return (await api.get<MonitorResult>("/forum/monitor/", { params })).data;
  },
  async remind(id: string): Promise<void> {
    await api.post(`/threads/${id}/remind/`);
  },
};

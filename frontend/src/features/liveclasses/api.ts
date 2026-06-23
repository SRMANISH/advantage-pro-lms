import { api } from "../../lib/api";

export interface LiveClass {
  id: string;
  batch: string;
  batch_code: string;
  title: string;
  scheduled_at: string;
  platform: string;
  meeting_link: string;
  checked_in: boolean | null;
  created_at: string;
}

export interface NewLiveClass {
  batch: string;
  title: string;
  scheduled_at: string;
  platform: string;
  meeting_link: string;
}

export const liveApi = {
  async list(batchId?: string): Promise<LiveClass[]> {
    return (await api.get<LiveClass[]>(`/liveclasses/${batchId ? `?batch=${batchId}` : ""}`)).data;
  },
  async create(payload: NewLiveClass): Promise<LiveClass> {
    return (await api.post<LiveClass>("/liveclasses/", payload)).data;
  },
  async checkIn(id: string): Promise<{ ok: boolean; meeting_link: string }> {
    return (await api.post(`/liveclasses/${id}/check-in/`)).data;
  },
};

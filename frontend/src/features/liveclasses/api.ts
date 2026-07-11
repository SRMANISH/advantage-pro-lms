import { api } from "../../lib/api";
import type { WeeklySchedule } from "../calendar/calendar";

export type LiveClassStatus = "scheduled" | "cancelled" | "completed";

export interface LiveClass {
  id: string;
  batch: string;
  batch_code: string;
  title: string;
  scheduled_at: string;
  duration_minutes: number;
  platform: string;
  meeting_link: string;
  status: LiveClassStatus;
  cancel_reason: string;
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
  async weeklySchedule(): Promise<WeeklySchedule[]> {
    return (await api.get<WeeklySchedule[]>("/liveclasses/weekly-schedule/")).data;
  },
  async create(payload: NewLiveClass): Promise<LiveClass> {
    return (await api.post<LiveClass>("/liveclasses/", payload)).data;
  },
  async checkIn(id: string): Promise<{ ok: boolean; meeting_link: string }> {
    return (await api.post(`/liveclasses/${id}/check-in/`)).data;
  },
  async cancel(id: string, reason?: string, confirmShortNotice?: boolean): Promise<void> {
    await api.post(`/liveclasses/${id}/cancel/`, {
      reason: reason ?? "",
      ...(confirmShortNotice ? { confirm_short_notice: true } : {}),
    });
  },
};

import { api } from "../../lib/api";

export interface NotificationItem {
  id: string;
  kind: string;
  message: string;
  link: string;
  read: boolean;
  created_at: string;
}

export const notificationsApi = {
  async list(): Promise<NotificationItem[]> {
    return (await api.get<NotificationItem[]>("/notifications/")).data;
  },
  async markRead(id: string): Promise<void> {
    await api.post(`/notifications/${id}/read/`);
  },
  async markAll(): Promise<void> {
    await api.post("/notifications/mark-all-read/");
  },
};

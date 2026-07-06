import { api, unwrap, type Paginated } from "../../lib/api";

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
    // The bell shows recent items; the first page (25) is the right amount.
    const { data } = await api.get<NotificationItem[] | Paginated<NotificationItem>>(
      "/notifications/",
    );
    return unwrap(data);
  },
  async markRead(id: string): Promise<void> {
    await api.post(`/notifications/${id}/read/`);
  },
  async markAll(): Promise<void> {
    await api.post("/notifications/mark-all-read/");
  },
};

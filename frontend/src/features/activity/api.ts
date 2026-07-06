import { api, unwrap, type Paginated } from "../../lib/api";

export interface ActivityRow {
  id: string;
  actor_name: string;
  action: string;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export const activityApi = {
  async list(): Promise<ActivityRow[]> {
    const { data } = await api.get<ActivityRow[] | Paginated<ActivityRow>>("/activity/", {
      params: { page_size: 100 },
    });
    return unwrap(data);
  },
};

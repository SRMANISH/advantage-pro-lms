import { api } from "../../lib/api";

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
    return (await api.get<ActivityRow[]>("/activity/")).data;
  },
};

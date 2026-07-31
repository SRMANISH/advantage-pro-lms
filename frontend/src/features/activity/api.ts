import { fetchPage, type Page } from "../../lib/api";

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
  /** Server-paginated. The audit log grows without bound, so a 100-row cap meant the page
   *  quietly stopped showing history the moment the platform got busy. */
  async list(params: Record<string, unknown> = {}): Promise<Page<ActivityRow>> {
    return fetchPage<ActivityRow>("/activity/", params);
  },
};

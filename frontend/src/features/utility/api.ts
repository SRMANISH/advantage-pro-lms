import { api } from "../../lib/api";

export interface UtilityLink {
  id: string;
  title: string;
  url: string;
  pinned: boolean;
  created_at: string;
}

/** Extract a YouTube video id so the notice board can show a real thumbnail. */
export function youtubeId(url: string): string | null {
  const m = url.match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([\w-]{6,})/);
  return m ? m[1] : null;
}

export function youtubeThumb(url: string): string | null {
  const id = youtubeId(url);
  return id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : null;
}

export const utilityApi = {
  async list(): Promise<UtilityLink[]> {
    return (await api.get<UtilityLink[]>("/utility-links/")).data;
  },
  async create(body: { title: string; url: string; pinned?: boolean }): Promise<UtilityLink> {
    return (await api.post<UtilityLink>("/utility-links/", body)).data;
  },
  async remove(id: string): Promise<void> {
    await api.delete(`/utility-links/${id}/`);
  },
};

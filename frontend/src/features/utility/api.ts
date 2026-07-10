import { api } from "../../lib/api";

export interface UtilityLink {
  id: string;
  title: string;
  url: string;
  pinned: boolean;
  /** MIS-uploaded thumbnail; null when none (board falls back to a YouTube/derived image). */
  thumbnail_url: string | null;
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
  async create(body: {
    title: string;
    url: string;
    pinned?: boolean;
    thumbnail?: File | null;
  }): Promise<UtilityLink> {
    if (body.thumbnail) {
      const form = new FormData();
      form.append("title", body.title);
      form.append("url", body.url);
      form.append("pinned", String(body.pinned ?? false));
      form.append("thumbnail", body.thumbnail);
      return (await api.post<UtilityLink>("/utility-links/", form)).data;
    }
    return (await api.post<UtilityLink>("/utility-links/", body)).data;
  },
  async remove(id: string): Promise<void> {
    await api.delete(`/utility-links/${id}/`);
  },
};

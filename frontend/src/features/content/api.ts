import { api } from "../../lib/api";

export interface VideoProgress {
  percent: number;
  completed: boolean;
  last_position: number;
}

export interface VideoItem {
  id: string;
  batch: string;
  title: string;
  description: string;
  content_type: string;
  uploaded_by_name?: string;
  play_url: string;
  progress: VideoProgress | null;
}

export interface MaterialItem {
  id: string;
  batch: string;
  title: string;
  content_type: string;
  view_url: string;
}

interface ProgressBody {
  percent: number;
  watched_seconds: number;
  last_position: number;
}

export const contentApi = {
  async listVideos(batchId?: string): Promise<VideoItem[]> {
    return (await api.get<VideoItem[]>(`/videos/${batchId ? `?batch=${batchId}` : ""}`)).data;
  },
  async uploadVideo(batchId: string, title: string, file: File): Promise<VideoItem> {
    const form = new FormData();
    form.append("batch", batchId);
    form.append("title", title);
    form.append("file", file);
    return (await api.post<VideoItem>("/videos/", form)).data;
  },
  async postProgress(id: string, body: ProgressBody): Promise<void> {
    await api.post(`/videos/${id}/progress/`, body);
  },
  async listMaterials(batchId?: string): Promise<MaterialItem[]> {
    return (await api.get<MaterialItem[]>(`/materials/${batchId ? `?batch=${batchId}` : ""}`)).data;
  },
  async uploadMaterial(batchId: string, title: string, file: File): Promise<MaterialItem> {
    const form = new FormData();
    form.append("batch", batchId);
    form.append("title", title);
    form.append("file", file);
    return (await api.post<MaterialItem>("/materials/", form)).data;
  },
  async closeCourseVideoAccess(batchId: string): Promise<void> {
    await api.post("/video-access/close-course/", { batch_id: batchId });
  },
  async revokeStudentVideoAccess(studentId: string, batchId?: string): Promise<void> {
    await api.post("/video-access/revoke/", { student_id: studentId, batch_id: batchId });
  },
};

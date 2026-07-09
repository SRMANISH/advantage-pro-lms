import { api } from "../../lib/api";

export interface FacultyProfile {
  skills: string;
  certifications: string;
  updated_at?: string;
}

export const facultyApi = {
  async getProfile(): Promise<FacultyProfile> {
    return (await api.get<FacultyProfile>("/auth/faculty/profile/")).data;
  },
  async saveProfile(payload: {
    skills: string;
    certifications: string;
  }): Promise<FacultyProfile> {
    return (await api.put<FacultyProfile>("/auth/faculty/profile/", payload)).data;
  },
};

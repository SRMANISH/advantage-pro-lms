import { api } from "../../lib/api";

export interface StaffUser {
  id: string;
  username: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
  status: string;
}

export interface NewStaff {
  username: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
}

export const staffApi = {
  async list(): Promise<StaffUser[]> {
    return (await api.get<StaffUser[]>("/auth/staff/")).data;
  },
  async create(body: NewStaff): Promise<StaffUser> {
    return (await api.post<StaffUser>("/auth/staff/", body)).data;
  },
};

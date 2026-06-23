import { api } from "../../lib/api";

export interface DeviceRequest {
  id: string;
  student_name: string;
  registration_number: string;
  created_at: string;
}

export const devicesApi = {
  async listRequests(): Promise<DeviceRequest[]> {
    return (await api.get<DeviceRequest[]>("/auth/devices/requests/")).data;
  },
  async decide(id: string, decision: "approve" | "reject"): Promise<void> {
    await api.post(`/auth/devices/requests/${id}/decide/`, { decision });
  },
};

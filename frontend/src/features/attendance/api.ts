import { api } from "../../lib/api";

export interface MyAttendanceRow {
  batch: string;
  batch_name: string;
  present: number;
  total: number;
  percent: number;
}

export interface RosterRow {
  student: string;
  student_name: string;
  registration_number: string;
  present: number;
  total: number;
  percent: number;
}

export interface BatchChoice {
  id: string;
  code: string;
  name: string;
}

export const attendanceApi = {
  async me(): Promise<MyAttendanceRow[]> {
    return (await api.get<MyAttendanceRow[]>("/attendance/me/")).data;
  },
  async batch(batchId: string): Promise<RosterRow[]> {
    return (await api.get<RosterRow[]>(`/attendance/?batch=${batchId}`)).data;
  },
  async reviewBatches(): Promise<BatchChoice[]> {
    return (await api.get<BatchChoice[]>("/attendance/batches/")).data;
  },
  async followUp(studentId: string, message?: string): Promise<void> {
    await api.post("/attendance/follow-up/", { student_id: studentId, message: message ?? "" });
  },
};

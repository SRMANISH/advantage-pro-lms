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

export type FollowUpStatus =
  | "pending"
  | "contacted"
  | "not_reachable"
  | "resolved"
  | "escalated";

export const FOLLOW_UP_STATUSES: { value: FollowUpStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "contacted", label: "Contacted" },
  { value: "not_reachable", label: "Not reachable" },
  { value: "resolved", label: "Resolved" },
  { value: "escalated", label: "Escalated" },
];

export interface DailyRow {
  student: string;
  student_name: string;
  registration_number: string;
  logged_in: boolean;
  follow_up_status: FollowUpStatus;
  follow_up_note: string;
}

export interface DailyResponse {
  date: string;
  rows: DailyRow[];
}

export const attendanceApi = {
  async me(): Promise<MyAttendanceRow[]> {
    return (await api.get<MyAttendanceRow[]>("/attendance/me/")).data;
  },
  async batch(batchId: string): Promise<RosterRow[]> {
    return (await api.get<RosterRow[]>(`/attendance/?batch=${batchId}`)).data;
  },
  async daily(batchId: string, date?: string): Promise<DailyResponse> {
    const q = date ? `&date=${date}` : "";
    return (await api.get<DailyResponse>(`/attendance/daily/?batch=${batchId}${q}`)).data;
  },
  async reviewBatches(): Promise<BatchChoice[]> {
    return (await api.get<BatchChoice[]>("/attendance/batches/")).data;
  },
  async followUp(studentId: string, message?: string): Promise<void> {
    await api.post("/attendance/follow-up/", { student_id: studentId, message: message ?? "" });
  },
  async setFollowUpStatus(
    batchId: string,
    studentId: string,
    status: FollowUpStatus,
    note?: string,
  ): Promise<void> {
    await api.post("/attendance/follow-up/status/", {
      batch: batchId,
      student_id: studentId,
      status,
      note: note ?? "",
    });
  },
};

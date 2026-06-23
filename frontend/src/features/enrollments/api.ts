import axios from "axios";

import { api } from "../../lib/api";

export interface RowError {
  row: number;
  field: string;
  message: string;
}

export interface ImportResult {
  valid: boolean;
  row_count?: number;
  created?: number;
  errors?: RowError[];
  detail?: string;
}

export interface EnrollmentRow {
  id: string;
  student: string;
  registration_number: string;
  student_name: string;
  student_status: string;
  email: string;
  phone: string;
  batch: string;
  batch_code: string;
  employment_company: string;
}

export const enrollmentsApi = {
  async importStudents(file: File, dryRun: boolean): Promise<ImportResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("dry_run", String(dryRun));
    try {
      const { data } = await api.post<ImportResult>("/enrollments/import/", form);
      return data;
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        return err.response.data as ImportResult;
      }
      throw err;
    }
  },
  async list(): Promise<EnrollmentRow[]> {
    return (await api.get<EnrollmentRow[]>("/enrollments/")).data;
  },
  async resendSetup(studentId: string): Promise<{ ok: boolean; url?: string }> {
    return (await api.post("/auth/setup/resend/", { student_id: studentId })).data;
  },
};

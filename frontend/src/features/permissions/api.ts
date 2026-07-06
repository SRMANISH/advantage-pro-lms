import { api } from "../../lib/api";

export interface RoleChoice {
  value: string;
  label: string;
}

export interface MatrixRow {
  action: string;
  roles: string[];
  default_roles: string[];
  overridden: boolean;
}

export interface MatrixResponse {
  roles: RoleChoice[];
  locked_super_admin_actions: string[];
  rows: MatrixRow[];
}

export const permissionsApi = {
  async matrix(): Promise<MatrixResponse> {
    return (await api.get<MatrixResponse>("/permissions/matrix/")).data;
  },
  async setRoles(action: string, roles: string[]): Promise<MatrixRow> {
    return (await api.put<MatrixRow>(`/permissions/matrix/${action}/`, { roles })).data;
  },
  async reset(action: string): Promise<MatrixRow> {
    return (await api.delete<MatrixRow>(`/permissions/matrix/${action}/`)).data;
  },
};

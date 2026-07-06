import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  SectionHeading,
  TableSkeleton,
  useToast,
} from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { permissionsApi, type MatrixRow } from "./api";

const prettyAction = (a: string) => a.replace(/_/g, " ");

export function PermissionsPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const matrix = useQuery({ queryKey: ["permission-matrix"], queryFn: permissionsApi.matrix });

  const save = useMutation({
    mutationFn: (vars: { action: string; roles: string[] }) =>
      permissionsApi.setRoles(vars.action, vars.roles),
    onSuccess: (row) => {
      qc.invalidateQueries({ queryKey: ["permission-matrix"] });
      toast.show(
        row.overridden
          ? `“${prettyAction(row.action)}” updated.`
          : `“${prettyAction(row.action)}” back to default.`,
        "success",
      );
    },
  });
  const reset = useMutation({
    mutationFn: (action: string) => permissionsApi.reset(action),
    onSuccess: (row) => {
      qc.invalidateQueries({ queryKey: ["permission-matrix"] });
      toast.show(`“${prettyAction(row.action)}” reset to default.`, "success");
    },
  });

  const roles = matrix.data?.roles ?? [];
  const locked = new Set(matrix.data?.locked_super_admin_actions ?? []);

  const toggle = (row: MatrixRow, roleValue: string) => {
    const next = row.roles.includes(roleValue)
      ? row.roles.filter((r) => r !== roleValue)
      : [...row.roles, roleValue];
    save.mutate({ action: row.action, roles: next });
  };

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Permissions"
        subtitle="Which roles may perform each action. Changes apply platform-wide within seconds; Reset returns an action to the built-in default."
      />
      <Card>
        {matrix.isLoading || !matrix.data ? (
          <TableSkeleton rows={8} cols={8} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-sky text-navy">
                <tr>
                  <th className="px-3 py-2 text-left">Action</th>
                  {roles.map((r) => (
                    <th key={r.value} className="px-2 py-2 text-center text-xs">
                      {r.label}
                    </th>
                  ))}
                  <th className="px-3 py-2 text-left">State</th>
                </tr>
              </thead>
              <tbody>
                {matrix.data.rows.map((row) => (
                  <tr key={row.action} className="border-t border-brdr">
                    <td className="px-3 py-2 font-medium capitalize text-ink">
                      {prettyAction(row.action)}
                    </td>
                    {roles.map((r) => {
                      const isLockedCell = locked.has(row.action) && r.value === "super_admin";
                      return (
                        <td key={r.value} className="px-2 py-2 text-center">
                          <input
                            type="checkbox"
                            aria-label={`${r.label} may ${prettyAction(row.action)}`}
                            checked={row.roles.includes(r.value)}
                            disabled={isLockedCell || save.isPending}
                            title={
                              isLockedCell
                                ? "Super Admin cannot be removed from this action (lockout guard)."
                                : undefined
                            }
                            onChange={() => toggle(row, r.value)}
                          />
                        </td>
                      );
                    })}
                    <td className="px-3 py-2">
                      {row.overridden ? (
                        <span className="inline-flex items-center gap-2">
                          <Badge tone="warning">custom</Badge>
                          <Button
                            variant="ghost"
                            onClick={() => reset.mutate(row.action)}
                            disabled={reset.isPending}
                          >
                            Reset
                          </Button>
                        </span>
                      ) : (
                        <span className="text-xs text-muted">default</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PortalLayout>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ROLES, type RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ListSkeleton,
  Paginator,
  QueryError,
  SectionHeading,
  Select,
  TableToolbar,
  useTableTools,
  useToast,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { staffApi } from "./api";

// Super Admin may create any staff role; Admin may create Counsellor only.
const ALL_STAFF_ROLES: { value: string; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "mis", label: "MIS Executive" },
  { value: "counselor", label: "Counsellor" },
  { value: "tech_support", label: "Tech Support" },
  { value: "faculty", label: "Faculty" },
];
/**
 * Roles that may be *assigned* from a row dropdown. Narrower than ROLE_LABEL on purpose: a
 * dropdown that cannot represent the row's own value silently displays its first option instead,
 * so a Super Admin row would read "Admin" and demote the account on the first change event.
 */
const ASSIGNABLE_ROLES = new Set(ALL_STAFF_ROLES.map((r) => r.value));

/**
 * Display labels for *every* role, not just the assignable ones. This previously covered only
 * ALL_STAFF_ROLES, so a Super Admin row fell through to the raw database value and rendered
 * "Super_admin" — underscore and all. ALL_STAFF_ROLES wins on overlap so the dropdown options
 * and the read-only badge never disagree on spelling.
 */
const ROLE_LABEL: Record<string, string> = {
  ...Object.fromEntries(ROLES.map((r) => [r.value, r.label])),
  ...Object.fromEntries(ALL_STAFF_ROLES.map((r) => [r.value, r.label])),
};

/** UserStatus rendered as a badge. Raw values ("active") must never reach the screen. */
const STATUS: Record<string, { label: string; tone: "success" | "warning" | "neutral" }> = {
  active: { label: "Active", tone: "success" },
  pending: { label: "Pending setup", tone: "neutral" },
  suspended: { label: "Suspended", tone: "warning" },
};

/**
 * Shared column track for every staff row. Fixed widths, not `justify-between`: the action button
 * renders on faculty rows only, and with content-driven widths its presence shoved that row's
 * role dropdown ~120px left of every other one. The action cell is now always reserved, so the
 * four columns line up whether or not a row has an action.
 */
const ROW_GRID = "sm:grid-cols-[minmax(0,1fr)_9.5rem_7rem_6rem]";

const empty = { username: "", full_name: "", email: "", phone: "", role: "" };

export function StaffPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";
  const roleOptions = isSuperAdmin
    ? ALL_STAFF_ROLES
    : ALL_STAFF_ROLES.filter((r) => r.value === "counselor");

  const staff = useQuery({ queryKey: ["staff"], queryFn: staffApi.list });
  // Search the *displayed* role, not the database value — the box promises "or role", and
  // searching "Super Admin" or "Counsellor" matched nothing against `super_admin`/`counselor`.
  const searchable = useMemo(
    () => staff.data?.map((s) => ({ ...s, role_label: ROLE_LABEL[s.role] ?? s.role })),
    [staff.data],
  );
  const table = useTableTools(searchable, ["username", "full_name", "role_label"], 8);
  const [form, setForm] = useState({ ...empty, role: roleOptions[0]?.value ?? "" });
  const [error, setError] = useState("");

  const canSuspendFaculty = isSuperAdmin || user?.role === "admin";

  const create = useMutation({
    mutationFn: () => staffApi.create(form),
    onSuccess: () => {
      setForm({ ...empty, role: roleOptions[0]?.value ?? "" });
      setError("");
      qc.invalidateQueries({ queryKey: ["staff"] });
      toast.show("Staff account created — setup link sent.", "success");
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string; username?: string[] } } })
        ?.response?.data;
      setError(detail?.detail ?? detail?.username?.[0] ?? "Could not create the account.");
    },
  });

  const setStatus = useMutation({
    mutationFn: (vars: { id: string; suspend: boolean }) =>
      staffApi.setStatus(vars.id, vars.suspend),
    onSuccess: (u) => {
      qc.invalidateQueries({ queryKey: ["staff"] });
      toast.show(
        u.status === "suspended" ? "Account suspended." : "Account reactivated.",
        "success",
      );
    },
  });

  const setRole = useMutation({
    mutationFn: (vars: { id: string; role: string }) => staffApi.setRole(vars.id, vars.role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff"] });
      toast.show("Role updated.", "success");
    },
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Staff accounts"
        subtitle={
          isSuperAdmin
            ? "Create any staff account. New staff finish the same two-step email + phone setup."
            : "Create Counsellor accounts. They finish the same two-step email + phone setup."
        }
      />

      <Card className="mb-6">
        <h2 className="mb-3 text-base font-medium text-ink">New staff member</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          <Input
            placeholder="Login ID"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
          <Input
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
          <Input
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Input
            placeholder="Phone"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
          <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {roleOptions.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </Select>
        </div>
        {error && (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <Button
          className="mt-3"
          onClick={() => create.mutate()}
          disabled={!form.username || !form.email || !form.role || create.isPending}
        >
          {create.isPending ? "Creating…" : "Create & send setup link"}
        </Button>
      </Card>

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Existing staff</h2>
        {staff.isLoading ? (
          <ListSkeleton items={3} />
        ) : staff.isError ? (
          <QueryError onRetry={() => staff.refetch()} />
        ) : staff.data && staff.data.length > 0 ? (
          <>
            <TableToolbar
              query={table.query}
              onQuery={table.setQuery}
              placeholder="Search staff by name, ID or role…"
            />
            <div className="flex flex-col divide-y divide-brdr">
              {table.rows.map((s) => {
                const status = STATUS[s.status] ?? { label: s.status, tone: "neutral" as const };
                return (
                  <div
                    key={s.id}
                    className={`grid grid-cols-1 items-center gap-2 py-2.5 text-sm sm:gap-3 ${ROW_GRID}`}
                  >
                    <div className="min-w-0 truncate">
                      <span className="font-medium text-ink">{s.full_name || s.username}</span>
                      <span className="text-muted"> · {s.username}</span>
                    </div>

                    {isSuperAdmin && ASSIGNABLE_ROLES.has(s.role) ? (
                      <Select
                        aria-label={`Role for ${s.username}`}
                        className="h-8 py-1 text-xs"
                        value={s.role}
                        onChange={(e) => setRole.mutate({ id: s.id, role: e.target.value })}
                      >
                        {ALL_STAFF_ROLES.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <div>
                        <Badge>{ROLE_LABEL[s.role] ?? s.role}</Badge>
                      </div>
                    )}

                    <div>
                      <Badge tone={status.tone}>{status.label}</Badge>
                    </div>

                    {/*
                      Always rendered so the columns stay aligned, but collapsed on mobile when
                      empty — a one-column stack would otherwise reserve a gap for nothing.

                      `h-8 text-xs` matches the Select, so a row is the same height with or
                      without an action. The padding needs `!`: cn() is a plain string join, not
                      tailwind-merge, so Button's base `px-4 py-2.5` is still in the class list
                      and Tailwind emits utilities in lexicographic order — `.px-4` lands after
                      `.px-3` and would win on equal specificity.
                    */}
                    <div className="empty:hidden sm:empty:block">
                      {canSuspendFaculty && s.role === "faculty" && s.status !== "pending" && (
                        <Button
                          variant="ghost"
                          className="h-8 w-full !px-3 !py-1 text-xs"
                          onClick={() =>
                            setStatus.mutate({ id: s.id, suspend: s.status !== "suspended" })
                          }
                        >
                          {s.status === "suspended" ? "Reactivate" : "Suspend"}
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            <Paginator
              page={table.page}
              pageCount={table.pageCount}
              onPage={table.setPage}
              total={table.total}
            />
          </>
        ) : (
          <EmptyState title="No staff accounts yet" />
        )}
      </Card>
    </PortalLayout>
  );
}

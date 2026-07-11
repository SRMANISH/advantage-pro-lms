import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Button,
  Card,
  ListSkeleton,
  ProgressRing,
  SectionHeading,
  TableSkeleton,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { attendanceApi, FOLLOW_UP_STATUSES, type FollowUpStatus } from "./api";

const todayIso = () => new Date().toISOString().slice(0, 10);

const FOLLOWUP_ROLES = new Set(["super_admin", "admin", "mis", "counselor"]);

function Bar({ percent }: { percent: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-sky">
      <div
        className="h-2 rounded-full bg-brand-strong"
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  );
}

export function AttendancePage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Attendance"
        subtitle="Login-based attendance and absentee follow-up."
      />
      {user?.role === "student" ? <MyAttendance /> : <BatchRoster />}
    </PortalLayout>
  );
}

function MyAttendance() {
  const rows = useQuery({ queryKey: ["attendance-me"], queryFn: attendanceApi.me });
  return (
    <div className="grid gap-4">
      {rows.isLoading ? (
        <ListSkeleton items={2} />
      ) : rows.data && rows.data.length > 0 ? (
        rows.data.map((r) => (
          <Card key={r.batch}>
            <div className="flex flex-wrap items-center gap-6">
              <ProgressRing value={r.percent} label="attendance" />
              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold text-ink">{r.batch_name}</h2>
                <p className="mt-1 text-sm text-muted">
                  You are present on{" "}
                  <span className="font-semibold text-ink">{r.present}</span> of{" "}
                  <span className="font-semibold text-ink">{r.total}</span> active days.
                </p>
                <p className="mt-0.5 text-xs text-muted">
                  Attendance is based on your daily login — sign in each day to keep it up.
                </p>
                <div className="mt-3 max-w-sm">
                  <Bar percent={r.percent} />
                </div>
              </div>
            </div>
          </Card>
        ))
      ) : (
        <Card>
          <p className="text-sm text-muted">No attendance yet.</p>
        </Card>
      )}
    </div>
  );
}

function BatchRoster() {
  const { user } = useAuth();
  const canFollowUp = FOLLOWUP_ROLES.has(user?.role ?? "");
  const batches = useQuery({
    queryKey: ["review-batches"],
    queryFn: attendanceApi.reviewBatches,
  });
  const [batchId, setBatchId] = useState("");
  const [sent, setSent] = useState<Set<string>>(new Set());
  const roster = useQuery({
    queryKey: ["attendance-batch", batchId],
    queryFn: () => attendanceApi.batch(batchId),
    enabled: !!batchId,
  });
  const followUp = useMutation({
    mutationFn: (studentId: string) => attendanceApi.followUp(studentId),
    onSuccess: (_d, studentId) => setSent((prev) => new Set(prev).add(studentId)),
  });

  return (
    <div className="grid gap-4">
      <Card>
        <label htmlFor="attendance-batch" className="mb-1 block text-sm text-muted">
          Batch
        </label>
        <select
          id="attendance-batch"
          className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
          value={batchId}
          onChange={(e) => setBatchId(e.target.value)}
        >
          <option value="">Select a batch…</option>
          {batches.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.code} — {b.name}
            </option>
          ))}
        </select>
      </Card>

      {batchId && (
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Roster</h2>
          {roster.data && roster.data.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-brdr">
              <table className="w-full text-sm">
                <thead className="bg-sky text-navy">
                  <tr>
                    <th className="px-3 py-2 text-left">Registration ID</th>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Present</th>
                    <th className="px-3 py-2 text-left">%</th>
                    {canFollowUp && <th className="px-3 py-2 text-left">Follow-up</th>}
                  </tr>
                </thead>
                <tbody>
                  {roster.data.map((r) => (
                    <tr key={r.registration_number} className="border-t border-brdr">
                      <td className="px-3 py-2">{r.registration_number}</td>
                      <td className="px-3 py-2">{r.student_name}</td>
                      <td className="px-3 py-2 text-muted">
                        {r.present}/{r.total}
                      </td>
                      <td className={`px-3 py-2 font-medium ${r.percent < 50 ? "text-red-600" : "text-navy"}`}>
                        {r.percent}%
                      </td>
                      {canFollowUp && (
                        <td className="px-3 py-2">
                          {sent.has(r.student) ? (
                            <span className="text-xs text-[color:var(--color-text-success,#1E8E5A)]">Sent ✓</span>
                          ) : (
                            <Button variant="ghost" onClick={() => followUp.mutate(r.student)}>
                              Send reminder
                            </Button>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted">No students in this batch.</p>
          )}
        </Card>
      )}

      {batchId && <DailyLoginPanel batchId={batchId} canFollowUp={canFollowUp} />}
    </div>
  );
}

function DailyLoginPanel({ batchId, canFollowUp }: { batchId: string; canFollowUp: boolean }) {
  const qc = useQueryClient();
  const [date, setDate] = useState(todayIso());
  const daily = useQuery({
    queryKey: ["attendance-daily", batchId, date],
    queryFn: () => attendanceApi.daily(batchId, date),
    enabled: !!batchId,
  });
  const setStatus = useMutation({
    mutationFn: ({
      studentId,
      status,
      note,
    }: {
      studentId: string;
      status: FollowUpStatus;
      note?: string;
    }) => attendanceApi.setFollowUpStatus(batchId, studentId, status, note),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["attendance-daily", batchId, date] }),
  });

  const rows = daily.data?.rows ?? [];
  const absentees = rows.filter((r) => !r.logged_in).length;

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-medium text-ink">Daily login attendance</h2>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted" htmlFor="daily-date">
            Date
          </label>
          <input
            id="daily-date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="h-9 rounded-lg border border-brdr bg-surface px-2 text-sm"
          />
        </div>
      </div>

      {daily.isLoading ? (
        <TableSkeleton rows={5} cols={4} />
      ) : rows.length > 0 ? (
        <>
          <p className="mb-2 text-xs text-muted">
            {rows.length - absentees} logged in · {absentees} did not log in
          </p>
          <div className="overflow-x-auto rounded-lg border border-brdr">
            <table className="w-full text-sm">
              <thead className="bg-sky text-navy">
                <tr>
                  <th className="px-3 py-2 text-left">Registration ID</th>
                  <th className="px-3 py-2 text-left">Name</th>
                  <th className="px-3 py-2 text-left">Logged in</th>
                  {canFollowUp && <th className="px-3 py-2 text-left">Follow-up</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.student} className="border-t border-brdr">
                    <td className="px-3 py-2">{r.registration_number}</td>
                    <td className="px-3 py-2">{r.student_name}</td>
                    <td className="px-3 py-2">
                      {r.logged_in ? (
                        <span className="text-[color:var(--color-text-success,#1E8E5A)]">✓ Yes</span>
                      ) : (
                        <span className="text-red-600">✗ No</span>
                      )}
                    </td>
                    {canFollowUp && (
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <select
                            className="h-9 rounded-lg border border-brdr bg-surface px-2 text-sm"
                            value={r.follow_up_status}
                            disabled={r.logged_in}
                            onChange={(e) =>
                              setStatus.mutate({
                                studentId: r.student,
                                status: e.target.value as FollowUpStatus,
                              })
                            }
                          >
                            {FOLLOW_UP_STATUSES.map((s) => (
                              <option key={s.value} value={s.value}>
                                {s.label}
                              </option>
                            ))}
                          </select>
                          <input
                            type="text"
                            aria-label={`Follow-up note for ${r.student_name}`}
                            placeholder="Add note…"
                            defaultValue={r.follow_up_note}
                            disabled={r.logged_in}
                            className="h-9 w-40 rounded-lg border border-brdr bg-surface px-2 text-sm"
                            onBlur={(e) => {
                              const note = e.target.value.trim();
                              if (note && note !== r.follow_up_note) {
                                setStatus.mutate({
                                  studentId: r.student,
                                  status: r.follow_up_status,
                                  note,
                                });
                              }
                            }}
                          />
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted">No students in this batch.</p>
      )}
    </Card>
  );
}

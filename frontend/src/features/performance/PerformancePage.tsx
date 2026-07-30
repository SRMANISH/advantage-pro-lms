import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  BatchSelect,
  Card,
  EmptyState,
  ListSkeleton,
  Paginator,
  SectionHeading,
  TableSkeleton,
  TableToolbar,
  useTableTools,
} from "../../design-system";
import { attendanceApi } from "../attendance/api";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { performanceApi, type PerfMetrics } from "./api";

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-sky px-3 py-2 text-center">
      <div className="text-lg font-medium text-navy">{value}%</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

function Metrics({ m }: { m: PerfMetrics }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <Metric label="Tests" value={m.test_pct} />
      <Metric label="Tasks" value={m.task_pct} />
      <Metric label="Videos" value={m.video_pct} />
      <Metric label="Attendance" value={m.attendance_pct} />
    </div>
  );
}

export function PerformancePage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Performance"
        subtitle="Composite of tests, tasks, videos and attendance."
      />
      {user?.role === "student" ? <MyPerformance /> : <BatchBoard />}
    </PortalLayout>
  );
}

function MyPerformance() {
  const rows = useQuery({ queryKey: ["perf-me"], queryFn: performanceApi.me });
  return (
    <div className="grid gap-4">
      {rows.isLoading ? (
        <ListSkeleton items={2} />
      ) : rows.data && rows.data.length > 0 ? (
        rows.data.map((r) => (
          <Card key={r.batch}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-medium text-ink">{r.batch_name}</h2>
              <div className="text-right">
                <div className="text-2xl font-medium text-navy">{r.overall}%</div>
                <div className="text-xs text-muted">
                  overall · rank {r.rank} of {r.size}
                </div>
              </div>
            </div>
            <Metrics m={r} />
          </Card>
        ))
      ) : (
        <EmptyState title="No performance data yet" />
      )}
    </div>
  );
}

function BatchBoard() {
  const batches = useQuery({ queryKey: ["review-batches"], queryFn: attendanceApi.reviewBatches });
  const [batchId, setBatchId] = useState("");
  const board = useQuery({
    queryKey: ["perf-batch", batchId],
    queryFn: () => performanceApi.batch(batchId),
    enabled: !!batchId,
  });
  const table = useTableTools(board.data, ["registration_number", "student_name"]);

  return (
    <div className="grid gap-4">
      <Card>
        <BatchSelect
          id="performance-batch"
          value={batchId}
          onChange={setBatchId}
          batches={batches.data}
        />
      </Card>

      {batchId && (
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Ranked performance</h2>
          {board.isLoading ? (
            <TableSkeleton rows={6} cols={8} />
          ) : board.data && board.data.length > 0 ? (
            <>
              <TableToolbar
                query={table.query}
                onQuery={table.setQuery}
                placeholder="Search by Registration ID or name…"
              />
              <div className="overflow-x-auto rounded-lg border border-brdr">
              <table className="w-full text-sm">
                <thead className="bg-sky text-navy">
                  <tr>
                    <th className="px-3 py-2 text-left">Rank</th>
                    <th className="px-3 py-2 text-left">Registration ID</th>
                    <th className="px-3 py-2 text-left">Student</th>
                    <th className="px-3 py-2 text-left">Tests</th>
                    <th className="px-3 py-2 text-left">Tasks</th>
                    <th className="px-3 py-2 text-left">Videos</th>
                    <th className="px-3 py-2 text-left">Att.</th>
                    <th className="px-3 py-2 text-left">Overall</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((r) => (
                    <tr key={r.student} className="border-t border-brdr">
                      <td className="px-3 py-2">{r.rank}</td>
                      <td className="px-3 py-2">{r.registration_number}</td>
                      <td className="px-3 py-2">{r.student_name}</td>
                      <td className="px-3 py-2 text-muted">{r.test_pct}%</td>
                      <td className="px-3 py-2 text-muted">{r.task_pct}%</td>
                      <td className="px-3 py-2 text-muted">{r.video_pct}%</td>
                      <td className="px-3 py-2 text-muted">{r.attendance_pct}%</td>
                      <td className="px-3 py-2 font-medium text-navy">{r.overall}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <Paginator
                page={table.page}
                pageCount={table.pageCount}
                onPage={table.setPage}
                total={table.total}
              />
            </>
          ) : (
            <EmptyState title="No students in this batch" />
          )}
        </Card>
      )}
    </div>
  );
}

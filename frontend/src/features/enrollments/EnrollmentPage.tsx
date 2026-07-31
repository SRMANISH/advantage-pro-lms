import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  FileUpload,
  Paginator,
  QueryError,
  SectionHeading,
  TableShell,
  TableSkeleton,
  TableToolbar,
  THead,
  useToast,
} from "../../design-system";
import { fetchPage } from "../../lib/api";
import { useServerTable } from "../../lib/useServerTable";
import { contentApi } from "../content/api";
import { PortalLayout } from "../portal/PortalLayout";
import { enrollmentsApi, type EnrollmentRow, type ImportResult } from "./api";

const TEMPLATE =
  "registration_number,name,email,phone,batch,course,faculty,address,guardian,employment_company\n" +
  "S001,Asha Rao,asha@example.com,9876543210,FS-DEMO,FS,faculty1,,,\n";

export function EnrollmentPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  // MIS may revoke/restore an individual student's video access (matrix
  // REVOKE_VIDEO_INDIVIDUAL); the roster is the natural place to do it per student.
  const isMis = role.value === "mis";
  const revokeVideos = useMutation({
    mutationFn: (vars: { studentId: string; batchId: string }) =>
      contentApi.revokeStudentVideoAccess(vars.studentId, vars.batchId),
    onSuccess: () => toast.show("Video access revoked for this student.", "success"),
  });
  const restoreVideos = useMutation({
    mutationFn: (vars: { studentId: string; batchId: string }) =>
      contentApi.restoreStudentVideoAccess(vars.studentId, vars.batchId),
    onSuccess: () => toast.show("Video access restored for this student.", "success"),
  });

  // Server-side pagination + search — a batch of thousands no longer truncates at 100.
  const table = useServerTable<EnrollmentRow>({
    key: ["enrollments"],
    searchable: true,
    fetcher: (p) => fetchPage<EnrollmentRow>("/enrollments/", p),
  });
  const [setupLinks, setSetupLinks] = useState<Record<string, string>>({});
  const resend = useMutation({
    mutationFn: (studentId: string) => enrollmentsApi.resendSetup(studentId),
    onSuccess: (data, studentId) => {
      if (data.url) setSetupLinks((prev) => ({ ...prev, [studentId]: data.url! }));
    },
  });

  const validate = useMutation({
    mutationFn: () => enrollmentsApi.importStudents(file!, true),
    onSuccess: setResult,
  });
  const confirm = useMutation({
    mutationFn: () => enrollmentsApi.importStudents(file!, false),
    onSuccess: (r) => {
      setResult(r);
      if (r.created != null) {
        setFile(null);
        qc.invalidateQueries({ queryKey: ["enrollments"] });
      }
    },
  });

  const downloadTemplate = () => {
    const url = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "student_import_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const validatedClean = result?.valid && result.created == null && result.row_count != null;

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Enrolment"
        subtitle="Import a clean student list — every row is validated before anything is saved."
        action={
          <Button variant="ghost" onClick={downloadTemplate}>
            Download template
          </Button>
        }
      />

      <Card className="mb-6">
        <h2 className="mb-1 text-base font-medium text-ink">Import student list</h2>
        <p className="mb-3 text-sm text-muted">
          Upload a .csv or .xlsx. The first column is each student&apos;s{" "}
          <span className="font-medium text-ink">Registration ID</span> (their login and recognition
          ID). If any row is invalid the whole upload is rejected and nothing is saved.
        </p>

        <FileUpload
          accept=".csv,.xlsx"
          file={file}
          onFile={(f) => {
            setFile(f);
            setResult(null);
          }}
          hint="CSV or XLSX · the first column must be the Registration ID"
        />
        <div className="mt-3">
          <Button onClick={() => validate.mutate()} disabled={!file || validate.isPending}>
            {validate.isPending ? "Validating…" : "Validate"}
          </Button>
        </div>

        {result?.detail && (
          <p className="mt-3 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {result.detail}
          </p>
        )}

        {result?.created != null && (
          <p className="mt-3 rounded-lg bg-success/10 px-3 py-2 text-sm text-success">
            ✓ Imported {result.created} student(s). They are now pending account setup.
          </p>
        )}

        {validatedClean && (
          <div className="mt-3 flex items-center gap-3 rounded-lg bg-sky px-3 py-2">
            <span className="text-sm text-navy">
              {result.row_count} row(s) valid — ready to import.
            </span>
            <Button onClick={() => confirm.mutate()} disabled={confirm.isPending}>
              {confirm.isPending ? "Importing…" : "Confirm import"}
            </Button>
          </div>
        )}

        {result?.valid === false && result.errors && (
          <div className="mt-3">
            <p className="mb-2 text-sm font-medium text-danger">
              {result.errors.length} problem(s) found — fix and re-upload:
            </p>
            <TableShell>
              <THead>
                <tr>
                  <th className="px-3 py-2">Row</th>
                  <th className="px-3 py-2">Field</th>
                  <th className="px-3 py-2">Problem</th>
                </tr>
              </THead>
              <tbody>
                {result.errors.map((e, i) => (
                  <tr key={i} className="border-t border-brdr">
                    <td className="px-3 py-2">{e.row}</td>
                    <td className="px-3 py-2">{e.field}</td>
                    <td className="px-3 py-2 text-muted">{e.message}</td>
                  </tr>
                ))}
              </tbody>
            </TableShell>
          </div>
        )}
      </Card>

      <SectionHeading title="Enrolled students" />
      {table.isLoading ? (
        <TableSkeleton rows={6} cols={6} />
      ) : table.isError ? (
        <QueryError onRetry={() => table.refetch()} />
      ) : table.total > 0 || table.query ? (
        <>
          <TableToolbar
            query={table.query}
            onQuery={table.setQuery}
            placeholder="Search by ID, name, batch or email…"
          />
          {table.rows.length === 0 ? (
            <EmptyState title="No matching students" hint="Try a different search." />
          ) : (
            <>
              <TableShell>
                <THead>
                  <tr>
                    <th className="px-3 py-2">Registration ID</th>
                    <th className="px-3 py-2">Name</th>
                    <th className="px-3 py-2">Batch</th>
                    <th className="px-3 py-2">Email</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Setup</th>
                    {isMis && <th className="px-3 py-2">Videos</th>}
                  </tr>
                </THead>
                <tbody>
                  {table.rows.map((s) => (
                    <tr key={s.id} className="border-t border-brdr">
                      <td className="px-3 py-2 font-medium text-ink">{s.registration_number}</td>
                      <td className="px-3 py-2">{s.student_name}</td>
                      <td className="px-3 py-2">{s.batch_code}</td>
                      <td className="px-3 py-2 text-muted">{s.email}</td>
                      <td className="px-3 py-2">
                        <Badge tone={s.student_status === "active" ? "success" : "warning"}>
                          {s.student_status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">
                        {s.student_status === "pending" &&
                          (setupLinks[s.student] ? (
                            <a
                              href={setupLinks[s.student]}
                              className="text-brand-strong underline"
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open link
                            </a>
                          ) : (
                            <Button variant="ghost" onClick={() => resend.mutate(s.student)}>
                              Setup link
                            </Button>
                          ))}
                      </td>
                      {isMis && (
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              onClick={() =>
                                revokeVideos.mutate({ studentId: s.student, batchId: s.batch })
                              }
                            >
                              Revoke
                            </Button>
                            <Button
                              variant="ghost"
                              onClick={() =>
                                restoreVideos.mutate({ studentId: s.student, batchId: s.batch })
                              }
                            >
                              Restore
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </TableShell>
              <Paginator
                page={table.page}
                pageCount={table.pageCount}
                onPage={table.setPage}
                total={table.total}
              />
            </>
          )}
        </>
      ) : (
        <EmptyState title="No students enrolled yet" hint="Import a list above to get started." />
      )}
    </PortalLayout>
  );
}

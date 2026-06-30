import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { enrollmentsApi, type ImportResult } from "./api";

const TEMPLATE =
  "registration_number,name,email,phone,batch,course,faculty,address,guardian,employment_company\n" +
  "S001,Asha Rao,asha@example.com,9876543210,FS-DEMO,FS,faculty1,,,\n";

export function EnrollmentPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const students = useQuery({ queryKey: ["enrollments"], queryFn: enrollmentsApi.list });
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
        if (fileRef.current) fileRef.current.value = "";
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
      <h1 className="mb-4 text-xl font-medium text-ink">Enrolment</h1>

      <Card className="mb-6">
        <h2 className="mb-1 text-base font-medium text-ink">Import student list</h2>
        <p className="mb-3 text-sm text-muted">
          Upload a .csv or .xlsx. The first column is each student&apos;s{" "}
          <span className="font-medium text-ink">Registration ID</span> (their login and
          recognition ID). Every row is validated; if any row is invalid the whole upload is
          rejected and nothing is saved.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setResult(null);
            }}
            className="text-sm"
          />
          <Button variant="ghost" onClick={downloadTemplate}>
            Download template
          </Button>
          <Button onClick={() => validate.mutate()} disabled={!file || validate.isPending}>
            {validate.isPending ? "Validating…" : "Validate"}
          </Button>
        </div>

        {result?.detail && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {result.detail}
          </p>
        )}

        {result?.created != null && (
          <p className="mt-3 text-sm text-[color:var(--color-text-success,#1E8E5A)]">
            ✓ Imported {result.created} student(s). They are now pending account setup.
          </p>
        )}

        {validatedClean && (
          <div className="mt-3 flex items-center gap-3 rounded-lg bg-sky px-3 py-2">
            <span className="text-sm text-navy">{result.row_count} row(s) valid — ready to import.</span>
            <Button onClick={() => confirm.mutate()} disabled={confirm.isPending}>
              {confirm.isPending ? "Importing…" : "Confirm import"}
            </Button>
          </div>
        )}

        {result?.valid === false && result.errors && (
          <div className="mt-3">
            <p className="mb-2 text-sm font-medium text-red-600">
              {result.errors.length} problem(s) found — fix and re-upload:
            </p>
            <div className="overflow-hidden rounded-lg border border-brdr">
              <table className="w-full text-sm">
                <thead className="bg-sky text-navy">
                  <tr>
                    <th className="px-3 py-2 text-left">Row</th>
                    <th className="px-3 py-2 text-left">Field</th>
                    <th className="px-3 py-2 text-left">Problem</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((e, i) => (
                    <tr key={i} className="border-t border-brdr">
                      <td className="px-3 py-2">{e.row}</td>
                      <td className="px-3 py-2">{e.field}</td>
                      <td className="px-3 py-2 text-muted">{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Enrolled students</h2>
        {students.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : students.data && students.data.length > 0 ? (
          <div className="overflow-hidden rounded-lg border border-brdr">
            <table className="w-full text-sm">
              <thead className="bg-sky text-navy">
                <tr>
                  <th className="px-3 py-2 text-left">Registration ID</th>
                  <th className="px-3 py-2 text-left">Name</th>
                  <th className="px-3 py-2 text-left">Batch</th>
                  <th className="px-3 py-2 text-left">Email</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Setup</th>
                </tr>
              </thead>
              <tbody>
                {students.data.map((s) => (
                  <tr key={s.id} className="border-t border-brdr">
                    <td className="px-3 py-2">{s.registration_number}</td>
                    <td className="px-3 py-2">{s.student_name}</td>
                    <td className="px-3 py-2">{s.batch_code}</td>
                    <td className="px-3 py-2 text-muted">{s.email}</td>
                    <td className="px-3 py-2">
                      <Badge>{s.student_status}</Badge>
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted">No students enrolled yet.</p>
        )}
      </Card>
    </PortalLayout>
  );
}

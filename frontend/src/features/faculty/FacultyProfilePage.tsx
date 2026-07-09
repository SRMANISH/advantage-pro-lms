import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Button, Card, SectionHeading, Spinner, useToast } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { facultyApi } from "./api";

/** Faculty maintain their skills + certifications here; these show when Super Admin/Admin
 *  choose faculty for a batch, so the right person is matched to the right course. */
export function FacultyProfilePage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const profile = useQuery({ queryKey: ["faculty-profile"], queryFn: facultyApi.getProfile });

  const [skills, setSkills] = useState("");
  const [certs, setCerts] = useState("");
  useEffect(() => {
    if (profile.data) {
      setSkills(profile.data.skills);
      setCerts(profile.data.certifications);
    }
  }, [profile.data]);

  const save = useMutation({
    mutationFn: () => facultyApi.saveProfile({ skills, certifications: certs }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["faculty-profile"] });
      toast.show("Profile saved.", "success");
    },
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="My skills & certifications"
        subtitle="Shown to admins when they assign faculty to batches — keep it current so you're matched to the right courses."
      />
      <Card className="max-w-xl">
        {profile.isLoading ? (
          <Spinner size={20} />
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <label htmlFor="fac-skills" className="mb-1 block text-xs font-medium text-muted">
                Skills (comma-separated)
              </label>
              <textarea
                id="fac-skills"
                className="min-h-20 w-full rounded-lg border border-brdr bg-surface p-2 text-sm"
                placeholder="e.g. React, Django, PostgreSQL, System Design"
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="fac-certs" className="mb-1 block text-xs font-medium text-muted">
                Certifications
              </label>
              <textarea
                id="fac-certs"
                className="min-h-20 w-full rounded-lg border border-brdr bg-surface p-2 text-sm"
                placeholder="e.g. AWS Solutions Architect, Google Cloud Professional"
                value={certs}
                onChange={(e) => setCerts(e.target.value)}
              />
            </div>
            <Button className="w-fit" onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending ? "Saving…" : "Save profile"}
            </Button>
          </div>
        )}
      </Card>
    </PortalLayout>
  );
}

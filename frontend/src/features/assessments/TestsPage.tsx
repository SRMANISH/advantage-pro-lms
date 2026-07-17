import type { RoleDef } from "../../app/roles";
import { SectionHeading } from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { ManageTests } from "./ManageTests";
import { StudentTests } from "./StudentTests";

/** Tests hub: faculty/admin build + grade (ManageTests); students take + submit
 * (StudentTests). The two flows live in their own files — see those for detail. */
export function TestsPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Tests"
        subtitle="Auto-graded MCQs, plus file (Excel) and Colab submissions graded by faculty."
      />
      {user?.role === "student" ? <StudentTests /> : <ManageTests />}
    </PortalLayout>
  );
}

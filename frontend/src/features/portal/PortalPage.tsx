import { useQuery } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import { EmptyState } from "../../design-system";
import { useAuth } from "../auth/auth";
import { dashboardApi, type DashboardData } from "../dashboard/api";
import { CounselorDashboard } from "./dashboards/CounselorDashboard";
import { FacultyDashboard } from "./dashboards/FacultyDashboard";
import { OpsDashboard } from "./dashboards/OpsDashboard";
import { DashboardSkeleton } from "./dashboards/shared";
import { StudentDashboard } from "./dashboards/StudentDashboard";
import { TechSupportDashboard } from "./dashboards/TechSupportDashboard";
import { PortalLayout } from "./PortalLayout";

export function PortalPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const name = user?.full_name || user?.username || "";
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: dashboardApi.get });

  return (
    <PortalLayout role={role}>
      {isLoading || !data ? (
        <DashboardSkeleton />
      ) : (
        <Dashboard role={role} data={data} name={name} />
      )}
    </PortalLayout>
  );
}

/** Each role gets its own dashboard component under ./dashboards — this just dispatches. */
function Dashboard({ role, data, name }: { role: RoleDef; data: DashboardData; name: string }) {
  const slug = role.slug;
  switch (data.role) {
    case "student":
      return <StudentDashboard data={data} name={name} slug={slug} />;
    case "faculty":
      return <FacultyDashboard data={data} name={name} slug={slug} />;
    case "super_admin":
    case "admin":
    case "mis":
      return <OpsDashboard data={data} slug={slug} />;
    case "counselor":
      return <CounselorDashboard data={data} slug={slug} />;
    case "tech_support":
      return <TechSupportDashboard data={data} slug={slug} />;
    default:
      return <EmptyState title="Your dashboard is being prepared." />;
  }
}

import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./app/ProtectedRoute";
import { ROLES } from "./app/roles";
import { Spinner } from "./design-system";

// Route-level code-splitting: each page is its own chunk, loaded on demand.
const LandingPage = lazy(() => import("./pages/LandingPage").then((m) => ({ default: m.LandingPage })));
const ShowcasePage = lazy(() => import("./pages/ShowcasePage").then((m) => ({ default: m.ShowcasePage })));
const SetupPage = lazy(() => import("./features/setup/SetupPage").then((m) => ({ default: m.SetupPage })));
const ForgotPasswordPage = lazy(() =>
  import("./features/auth/ForgotPasswordPage").then((m) => ({ default: m.ForgotPasswordPage })),
);
const LoginPage = lazy(() => import("./features/auth/LoginPage").then((m) => ({ default: m.LoginPage })));
const PortalPage = lazy(() => import("./features/portal/PortalPage").then((m) => ({ default: m.PortalPage })));
const BatchesPage = lazy(() => import("./features/batches/BatchesPage").then((m) => ({ default: m.BatchesPage })));
const StaffPage = lazy(() => import("./features/staff/StaffPage").then((m) => ({ default: m.StaffPage })));
const EnrollmentPage = lazy(() =>
  import("./features/enrollments/EnrollmentPage").then((m) => ({ default: m.EnrollmentPage })),
);
const ContentPage = lazy(() => import("./features/content/ContentPage").then((m) => ({ default: m.ContentPage })));
const LearningPage = lazy(() => import("./features/content/LearningPage").then((m) => ({ default: m.LearningPage })));
const TestsPage = lazy(() => import("./features/assessments/TestsPage").then((m) => ({ default: m.TestsPage })));
const TasksPage = lazy(() => import("./features/assessments/TasksPage").then((m) => ({ default: m.TasksPage })));
const AttendancePage = lazy(() =>
  import("./features/attendance/AttendancePage").then((m) => ({ default: m.AttendancePage })),
);
const PerformancePage = lazy(() =>
  import("./features/performance/PerformancePage").then((m) => ({ default: m.PerformancePage })),
);
const DevicesPage = lazy(() => import("./features/devices/DevicesPage").then((m) => ({ default: m.DevicesPage })));
const ActivityPage = lazy(() => import("./features/activity/ActivityPage").then((m) => ({ default: m.ActivityPage })));
const EngagementReportPage = lazy(() =>
  import("./features/engagement/EngagementReportPage").then((m) => ({ default: m.EngagementReportPage })),
);
const EscalationsPage = lazy(() =>
  import("./features/escalations/EscalationsPage").then((m) => ({ default: m.EscalationsPage })),
);
const ForumPage = lazy(() => import("./features/forum/ForumPage").then((m) => ({ default: m.ForumPage })));
const MonitorPage = lazy(() => import("./features/forum/MonitorPage").then((m) => ({ default: m.MonitorPage })));
const LiveClassesPage = lazy(() =>
  import("./features/liveclasses/LiveClassesPage").then((m) => ({ default: m.LiveClassesPage })),
);
const ChannelsPage = lazy(() => import("./features/channels/ChannelsPage").then((m) => ({ default: m.ChannelsPage })));
const SecurityPage = lazy(() =>
  import("./features/auth/SecurityPage").then((m) => ({ default: m.SecurityPage })),
);
const CoursesPage = lazy(() =>
  import("./features/batches/CoursesPage").then((m) => ({ default: m.CoursesPage })),
);
const FacultyProfilePage = lazy(() =>
  import("./features/faculty/FacultyProfilePage").then((m) => ({ default: m.FacultyProfilePage })),
);
const CalendarPage = lazy(() =>
  import("./features/calendar/CalendarPage").then((m) => ({ default: m.CalendarPage })),
);
const GoodiesPage = lazy(() =>
  import("./features/welcome/GoodiesPage").then((m) => ({ default: m.GoodiesPage })),
);
const PermissionsPage = lazy(() =>
  import("./features/permissions/PermissionsPage").then((m) => ({ default: m.PermissionsPage })),
);
const CertificatePage = lazy(() =>
  import("./features/certification/CertificatePage").then((m) => ({ default: m.CertificatePage })),
);
const CertFollowUpPage = lazy(() =>
  import("./features/certification/CertFollowUpPage").then((m) => ({ default: m.CertFollowUpPage })),
);
const ReportsPage = lazy(() => import("./features/reports/ReportsPage").then((m) => ({ default: m.ReportsPage })));
const ChangePasswordPage = lazy(() =>
  import("./features/auth/ChangePasswordPage").then((m) => ({ default: m.ChangePasswordPage })),
);
const UtilityLinksPage = lazy(() =>
  import("./features/utility/UtilityLinksPage").then((m) => ({ default: m.UtilityLinksPage })),
);
const UtilityLinksBoardPage = lazy(() =>
  import("./pages/UtilityLinksBoardPage").then((m) => ({ default: m.UtilityLinksBoardPage })),
);

// Route guards mirror the updated permission matrix (and PortalLayout NAV). UI hiding only;
// the backend enforces the matrix on every endpoint.
const BATCH_ROLES = new Set(["admin", "mis", "faculty"]);
const ENROL_ROLES = new Set(["admin", "mis"]);
const STAFF_ROLES = new Set(["super_admin"]);
const CONTENT_ROLES = new Set(["mis", "faculty"]);
const TEST_ROLES = new Set(["mis", "faculty", "student"]);
const TASK_ROLES = new Set(["mis", "faculty", "student"]);
const ATTEND_ROLES = new Set(["super_admin", "admin", "mis", "faculty", "student", "counselor"]);
const PERF_ROLES = new Set(["super_admin", "admin", "mis", "faculty", "student", "counselor"]);
const DEVICE_ROLES = new Set(["mis", "tech_support", "faculty"]);
const ACTIVITY_ROLES = new Set(["mis", "faculty"]);
const CERT_FOLLOWUP_ROLES = new Set(["admin", "mis"]);
const ENGAGEMENT_ROLES = new Set(["admin", "mis"]);
const ESCALATION_ROLES = new Set(["super_admin", "admin", "mis"]);
const FORUM_ROLES = new Set(["tech_support", "faculty", "student"]);
const MONITOR_ROLES = new Set(["tech_support"]);
const LIVE_ROLES = new Set(["admin", "mis", "faculty", "student"]);
const SETTINGS_ROLES = new Set(["super_admin"]);
const REPORT_ROLES = new Set(["super_admin", "admin", "mis", "counselor", "faculty"]);
// TOTP 2FA is a staff feature — every role except student.
const STAFF_ROLES_ALL = new Set(["super_admin", "admin", "mis", "counselor", "tech_support", "faculty"]);

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-appbg">
      <Spinner size={28} />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        {/* Design-system demo page — dev builds only, never a public prod surface. */}
        {import.meta.env.DEV && <Route path="/showcase" element={<ShowcasePage />} />}
        <Route path="/setup/:token" element={<SetupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/utility-links" element={<UtilityLinksBoardPage />} />
        {ROLES.map((role) => (
          <Route
            key={`login-${role.slug}`}
            path={`/login/${role.slug}`}
            element={<LoginPage role={role} />}
          />
        ))}
        {ROLES.map((role) => (
          <Route
            key={`portal-${role.slug}`}
            path={`/${role.slug}`}
            element={
              <ProtectedRoute role={role}>
                <PortalPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => STAFF_ROLES_ALL.has(role.value)).map((role) => (
          <Route
            key={`security-${role.slug}`}
            path={`/${role.slug}/security`}
            element={
              <ProtectedRoute role={role}>
                <SecurityPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.map((role) => (
          <Route
            key={`change-password-${role.slug}`}
            path={`/${role.slug}/change-password`}
            element={
              <ProtectedRoute role={role}>
                <ChangePasswordPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => BATCH_ROLES.has(role.value)).map((role) => (
          <Route
            key={`batches-${role.slug}`}
            path={`/${role.slug}/batches`}
            element={
              <ProtectedRoute role={role}>
                <BatchesPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => role.value === "super_admin").map((role) => (
          <Route
            key={`courses-${role.slug}`}
            path={`/${role.slug}/courses`}
            element={
              <ProtectedRoute role={role}>
                <CoursesPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => role.value === "faculty").map((role) => (
          <Route
            key={`profile-${role.slug}`}
            path={`/${role.slug}/profile`}
            element={
              <ProtectedRoute role={role}>
                <FacultyProfilePage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => role.value === "student").map((role) => (
          <Route
            key={`calendar-${role.slug}`}
            path={`/${role.slug}/calendar`}
            element={
              <ProtectedRoute role={role}>
                <CalendarPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => STAFF_ROLES.has(role.value)).map((role) => (
          <Route
            key={`staff-${role.slug}`}
            path={`/${role.slug}/staff`}
            element={
              <ProtectedRoute role={role}>
                <StaffPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => ENROL_ROLES.has(role.value)).map((role) => (
          <Route
            key={`goodies-${role.slug}`}
            path={`/${role.slug}/goodies`}
            element={
              <ProtectedRoute role={role}>
                <GoodiesPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => ENROL_ROLES.has(role.value)).map((role) => (
          <Route
            key={`enrolment-${role.slug}`}
            path={`/${role.slug}/enrolment`}
            element={
              <ProtectedRoute role={role}>
                <EnrollmentPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => CONTENT_ROLES.has(role.value)).map((role) => (
          <Route
            key={`content-${role.slug}`}
            path={`/${role.slug}/content`}
            element={
              <ProtectedRoute role={role}>
                <ContentPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => role.value === "student").map((role) => (
          <Route
            key={`videos-${role.slug}`}
            path={`/${role.slug}/videos`}
            element={
              <ProtectedRoute role={role}>
                <LearningPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => TEST_ROLES.has(role.value)).map((role) => (
          <Route
            key={`tests-${role.slug}`}
            path={`/${role.slug}/tests`}
            element={
              <ProtectedRoute role={role}>
                <TestsPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => TASK_ROLES.has(role.value)).map((role) => (
          <Route
            key={`tasks-${role.slug}`}
            path={`/${role.slug}/tasks`}
            element={
              <ProtectedRoute role={role}>
                <TasksPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => ATTEND_ROLES.has(role.value)).map((role) => (
          <Route
            key={`attendance-${role.slug}`}
            path={`/${role.slug}/attendance`}
            element={
              <ProtectedRoute role={role}>
                <AttendancePage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => PERF_ROLES.has(role.value)).map((role) => (
          <Route
            key={`performance-${role.slug}`}
            path={`/${role.slug}/performance`}
            element={
              <ProtectedRoute role={role}>
                <PerformancePage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => DEVICE_ROLES.has(role.value)).map((role) => (
          <Route
            key={`devices-${role.slug}`}
            path={`/${role.slug}/devices`}
            element={
              <ProtectedRoute role={role}>
                <DevicesPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => ACTIVITY_ROLES.has(role.value)).map((role) => (
          <Route
            key={`activity-${role.slug}`}
            path={`/${role.slug}/activity`}
            element={
              <ProtectedRoute role={role}>
                <ActivityPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => ENGAGEMENT_ROLES.has(role.value)).map((role) => (
          <Route
            key={`engagement-${role.slug}`}
            path={`/${role.slug}/engagement`}
            element={
              <ProtectedRoute role={role}>
                <EngagementReportPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => role.value === "mis").map((role) => (
          <Route
            key={`utility-${role.slug}`}
            path={`/${role.slug}/utility-links`}
            element={
              <ProtectedRoute role={role}>
                <UtilityLinksPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => ESCALATION_ROLES.has(role.value)).map((role) => (
          <Route
            key={`escalations-${role.slug}`}
            path={`/${role.slug}/escalations`}
            element={
              <ProtectedRoute role={role}>
                <EscalationsPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => FORUM_ROLES.has(role.value)).map((role) => (
          <Route
            key={`forum-${role.slug}`}
            path={`/${role.slug}/forum`}
            element={
              <ProtectedRoute role={role}>
                <ForumPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => MONITOR_ROLES.has(role.value)).map((role) => (
          <Route
            key={`monitor-${role.slug}`}
            path={`/${role.slug}/monitor`}
            element={
              <ProtectedRoute role={role}>
                <MonitorPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => LIVE_ROLES.has(role.value)).map((role) => (
          <Route
            key={`live-${role.slug}`}
            path={`/${role.slug}/live`}
            element={
              <ProtectedRoute role={role}>
                <LiveClassesPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => SETTINGS_ROLES.has(role.value)).map((role) => (
          <Route
            key={`channels-${role.slug}`}
            path={`/${role.slug}/channels`}
            element={
              <ProtectedRoute role={role}>
                <ChannelsPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => SETTINGS_ROLES.has(role.value)).map((role) => (
          <Route
            key={`permissions-${role.slug}`}
            path={`/${role.slug}/permissions`}
            element={
              <ProtectedRoute role={role}>
                <PermissionsPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => role.value === "student").map((role) => (
          <Route
            key={`certificate-${role.slug}`}
            path={`/${role.slug}/certificate`}
            element={
              <ProtectedRoute role={role}>
                <CertificatePage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => CERT_FOLLOWUP_ROLES.has(role.value)).map((role) => (
          <Route
            key={`certificates-${role.slug}`}
            path={`/${role.slug}/certificates`}
            element={
              <ProtectedRoute role={role}>
                <CertFollowUpPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        {ROLES.filter((role) => REPORT_ROLES.has(role.value)).map((role) => (
          <Route
            key={`reports-${role.slug}`}
            path={`/${role.slug}/reports`}
            element={
              <ProtectedRoute role={role}>
                <ReportsPage role={role} />
              </ProtectedRoute>
            }
          />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

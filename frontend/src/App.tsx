import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./app/ProtectedRoute";
import { ROLES } from "./app/roles";
import { ActivityPage } from "./features/activity/ActivityPage";
import { BatchesPage } from "./features/batches/BatchesPage";
import { CertFollowUpPage } from "./features/certification/CertFollowUpPage";
import { EngagementReportPage } from "./features/engagement/EngagementReportPage";
import { ForgotPasswordPage } from "./features/auth/ForgotPasswordPage";
import { LoginPage } from "./features/auth/LoginPage";
import { TasksPage } from "./features/assessments/TasksPage";
import { TestsPage } from "./features/assessments/TestsPage";
import { AttendancePage } from "./features/attendance/AttendancePage";
import { CertificatePage } from "./features/certification/CertificatePage";
import { ChannelsPage } from "./features/channels/ChannelsPage";
import { DevicesPage } from "./features/devices/DevicesPage";
import { EscalationsPage } from "./features/escalations/EscalationsPage";
import { ForumPage } from "./features/forum/ForumPage";
import { MonitorPage } from "./features/forum/MonitorPage";
import { LiveClassesPage } from "./features/liveclasses/LiveClassesPage";
import { PerformancePage } from "./features/performance/PerformancePage";
import { ContentPage } from "./features/content/ContentPage";
import { LearningPage } from "./features/content/LearningPage";
import { EnrollmentPage } from "./features/enrollments/EnrollmentPage";
import { PortalPage } from "./features/portal/PortalPage";
import { ReportsPage } from "./features/reports/ReportsPage";
import { SetupPage } from "./features/setup/SetupPage";
import { LandingPage } from "./pages/LandingPage";
import { ShowcasePage } from "./pages/ShowcasePage";

// Route guards mirror the updated permission matrix (and PortalLayout NAV). UI hiding only;
// the backend enforces the matrix on every endpoint.
const BATCH_ROLES = new Set(["admin", "mis", "faculty"]);
const ENROL_ROLES = new Set(["admin", "mis"]);
const CONTENT_ROLES = new Set(["mis", "faculty"]);
const TEST_ROLES = new Set(["mis", "faculty", "student"]);
const TASK_ROLES = new Set(["faculty", "student"]);
const ATTEND_ROLES = new Set(["super_admin", "admin", "mis", "faculty", "student", "counselor"]);
const PERF_ROLES = new Set(["super_admin", "admin", "mis", "faculty", "student", "counselor"]);
const DEVICE_ROLES = new Set(["mis", "faculty"]);
const ACTIVITY_ROLES = new Set(["mis", "faculty"]);
const CERT_FOLLOWUP_ROLES = new Set(["admin", "mis"]);
const ENGAGEMENT_ROLES = new Set(["admin", "mis"]);
const ESCALATION_ROLES = new Set(["super_admin", "admin", "mis"]);
const FORUM_ROLES = new Set(["mis", "tech_support", "faculty", "student"]);
const MONITOR_ROLES = new Set(["mis", "tech_support"]);
const LIVE_ROLES = new Set(["admin", "mis", "faculty", "student"]);
const SETTINGS_ROLES = new Set(["super_admin"]);
const REPORT_ROLES = new Set(["super_admin", "admin", "mis", "counselor", "faculty"]);

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/showcase" element={<ShowcasePage />} />
      <Route path="/setup/:token" element={<SetupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
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
  );
}

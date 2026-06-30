import {
  Activity,
  Award,
  BarChart3,
  CalendarCheck,
  ClipboardList,
  Download,
  Eye,
  FileText,
  LayoutDashboard,
  type LucideIcon,
  Menu,
  MessagesSquare,
  PlayCircle,
  Radio,
  Settings,
  Smartphone,
  Sparkles,
  TriangleAlert,
  UserPlus,
  Users,
  Video,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Button, Logo, cn } from "../../design-system";
import { useAuth } from "../auth/auth";
import { NotificationBell } from "../notifications/NotificationBell";

const role = (...values: string[]) => new Set(values);
// Visibility sets mirror the updated permission matrix (backend is the source of truth;
// these only hide UI). Super Admin is intentionally out of operational flows.
const ALL = role("super_admin", "admin", "mis", "counselor", "tech_support", "faculty", "student");
const BATCHES = role("admin", "mis", "faculty"); // Admin manages, MIS/Faculty view
const ADMIN_MIS = role("admin", "mis"); // enrolment/import
const CONTENT = role("mis", "faculty"); // notes (MIS+FAC), videos (FAC)
const TESTS = role("mis", "faculty", "student"); // MCQ build = MIS+FAC; student takes
const TASKS = role("faculty", "student"); // Faculty assigns; student submits
const LIVE = role("admin", "mis", "faculty", "student"); // Faculty schedules; others view
const ATTEND = role("super_admin", "admin", "mis", "faculty", "student", "counselor");
const FORUM = role("mis", "tech_support", "faculty", "student"); // no SA/AD moderation
const MONITOR = role("mis", "tech_support"); // doubt monitor
const DEVICES = role("mis", "faculty"); // approve device change (MIS outside / FAC in class)
const ACTIVITY = role("mis", "faculty"); // activity/audit access (no SA/AD)
const ESCALATIONS = role("super_admin", "admin", "mis");
const REPORTS = role("super_admin", "admin", "mis", "counselor", "faculty");

interface NavEntry {
  to: string;
  label: string;
  Icon: LucideIcon;
  roles: Set<string>;
}

const NAV: NavEntry[] = [
  { to: "", label: "Dashboard", Icon: LayoutDashboard, roles: ALL },
  { to: "batches", label: "Batches", Icon: Users, roles: BATCHES },
  { to: "enrolment", label: "Enrolment", Icon: UserPlus, roles: ADMIN_MIS },
  { to: "content", label: "Content", Icon: Video, roles: CONTENT },
  { to: "videos", label: "Videos", Icon: PlayCircle, roles: role("student") },
  { to: "tests", label: "Tests", Icon: ClipboardList, roles: TESTS },
  { to: "tasks", label: "Tasks", Icon: FileText, roles: TASKS },
  { to: "live", label: "Live classes", Icon: Radio, roles: LIVE },
  { to: "attendance", label: "Attendance", Icon: CalendarCheck, roles: ATTEND },
  { to: "performance", label: "Performance", Icon: BarChart3, roles: ATTEND },
  { to: "forum", label: "Forum", Icon: MessagesSquare, roles: FORUM },
  { to: "monitor", label: "Doubt monitor", Icon: Eye, roles: MONITOR },
  { to: "certificate", label: "Certificate", Icon: Award, roles: role("student") },
  { to: "certificates", label: "Certificates", Icon: Award, roles: role("admin", "mis") },
  { to: "devices", label: "Devices", Icon: Smartphone, roles: DEVICES },
  { to: "activity", label: "Activity", Icon: Activity, roles: ACTIVITY },
  { to: "escalations", label: "Escalations", Icon: TriangleAlert, roles: ESCALATIONS },
  { to: "engagement", label: "Engagement", Icon: Sparkles, roles: ADMIN_MIS },
  { to: "reports", label: "Reports", Icon: Download, roles: REPORTS },
  { to: "channels", label: "Channels", Icon: Settings, roles: role("super_admin") },
];

export function PortalLayout({ role: roleDef, children }: { role: RoleDef; children: ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const name = user?.full_name || user?.username;

  const items = NAV.filter((n) => n.roles.has(roleDef.value));
  const pathFor = (to: string) => (to ? `/${roleDef.slug}/${to}` : `/${roleDef.slug}`);

  const sidebar = (
    <>
      <Link
        to={`/${roleDef.slug}`}
        onClick={() => setOpen(false)}
        className="flex items-center gap-2 border-b border-brdr px-4 py-3"
      >
        <Logo size={34} />
      </Link>
      <div className="px-4 pb-1 pt-3 text-xs uppercase tracking-wide text-muted">
        {roleDef.label}
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        {items.map(({ to, label, Icon }) => {
          const active = location.pathname === pathFor(to);
          return (
            <Link
              key={label}
              to={pathFor(to)}
              onClick={() => setOpen(false)}
              className={cn(
                "mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm",
                active ? "bg-sky font-medium text-navy" : "text-muted hover:bg-sky hover:text-navy",
              )}
            >
              <Icon size={18} aria-hidden /> {label}
            </Link>
          );
        })}
      </nav>
    </>
  );

  return (
    <div className="flex min-h-screen bg-appbg">
      <aside className="hidden w-60 flex-col border-r border-brdr bg-surface md:flex">{sidebar}</aside>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-60 flex-col bg-surface">{sidebar}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-brdr bg-surface px-4">
          <button className="md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <span className="text-sm font-medium text-navy md:hidden">{roleDef.label}</span>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <NotificationBell />
            <span className="hidden text-sm text-muted sm:inline">{name}</span>
            <Button variant="ghost" onClick={() => void logout()}>
              Sign out
            </Button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

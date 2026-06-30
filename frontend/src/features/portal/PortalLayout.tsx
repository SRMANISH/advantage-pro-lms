import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Award,
  BarChart3,
  CalendarCheck,
  ChevronDown,
  ClipboardList,
  Download,
  Eye,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  type LucideIcon,
  Menu,
  MessagesSquare,
  PlayCircle,
  Radio,
  Settings,
  Smartphone,
  Sparkles,
  TriangleAlert,
  UserCog,
  UserPlus,
  Users,
  Video,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Avatar, Logo, cn, pageVariants } from "../../design-system";
import { useAuth } from "../auth/auth";
import { EngagementPrompts } from "../engagement/EngagementPrompts";
import { NotificationBell } from "../notifications/NotificationBell";

const role = (...values: string[]) => new Set(values);
// Visibility sets mirror the updated permission matrix (backend is the source of truth;
// these only hide UI). Super Admin is intentionally out of operational flows.
const ALL = role("super_admin", "admin", "mis", "counselor", "tech_support", "faculty", "student");
const BATCHES = role("admin", "mis", "faculty");
const ADMIN_MIS = role("admin", "mis");
const CONTENT = role("mis", "faculty");
const TESTS = role("mis", "faculty", "student");
const TASKS = role("mis", "faculty", "student");
const LIVE = role("admin", "mis", "faculty", "student");
const ATTEND = role("super_admin", "admin", "mis", "faculty", "student", "counselor");
const FORUM = role("mis", "tech_support", "faculty", "student");
const MONITOR = role("mis", "tech_support");
const DEVICES = role("mis", "faculty");
const ACTIVITY = role("mis", "faculty");
const ESCALATIONS = role("super_admin", "admin", "mis");
const REPORTS = role("super_admin", "admin", "mis", "counselor", "faculty");

interface NavEntry {
  to: string;
  label: string;
  Icon: LucideIcon;
  roles: Set<string>;
  group: string;
}

const NAV: NavEntry[] = [
  { to: "", label: "Dashboard", Icon: LayoutDashboard, roles: ALL, group: "Overview" },
  { to: "batches", label: "Batches", Icon: Users, roles: BATCHES, group: "People & batches" },
  { to: "enrolment", label: "Enrolment", Icon: UserPlus, roles: ADMIN_MIS, group: "People & batches" },
  { to: "staff", label: "Staff", Icon: UserCog, roles: role("super_admin", "admin"), group: "People & batches" },
  { to: "content", label: "Content", Icon: Video, roles: CONTENT, group: "Learning" },
  { to: "videos", label: "Videos", Icon: PlayCircle, roles: role("student"), group: "Learning" },
  { to: "tests", label: "Tests", Icon: ClipboardList, roles: TESTS, group: "Learning" },
  { to: "tasks", label: "Tasks", Icon: FileText, roles: TASKS, group: "Learning" },
  { to: "live", label: "Live classes", Icon: Radio, roles: LIVE, group: "Learning" },
  { to: "attendance", label: "Attendance", Icon: CalendarCheck, roles: ATTEND, group: "Tracking" },
  { to: "performance", label: "Performance", Icon: BarChart3, roles: ATTEND, group: "Tracking" },
  { to: "forum", label: "Forum", Icon: MessagesSquare, roles: FORUM, group: "Tracking" },
  { to: "monitor", label: "Doubt monitor", Icon: Eye, roles: MONITOR, group: "Tracking" },
  { to: "activity", label: "Activity", Icon: Activity, roles: ACTIVITY, group: "Tracking" },
  { to: "certificate", label: "Certificate", Icon: Award, roles: role("student"), group: "Completion" },
  { to: "certificates", label: "Certificates", Icon: Award, roles: role("admin", "mis"), group: "Completion" },
  { to: "engagement", label: "Engagement", Icon: Sparkles, roles: ADMIN_MIS, group: "Completion" },
  { to: "devices", label: "Devices", Icon: Smartphone, roles: DEVICES, group: "Operations" },
  { to: "escalations", label: "Escalations", Icon: TriangleAlert, roles: ESCALATIONS, group: "Operations" },
  { to: "reports", label: "Reports", Icon: Download, roles: REPORTS, group: "Operations" },
  { to: "channels", label: "Channels", Icon: Settings, roles: role("super_admin"), group: "Operations" },
];

const GROUP_ORDER = ["Overview", "People & batches", "Learning", "Tracking", "Completion", "Operations"];

export function PortalLayout({ role: roleDef, children }: { role: RoleDef; children: ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const name = user?.full_name || user?.username || "";

  const items = NAV.filter((n) => n.roles.has(roleDef.value));
  const pathFor = (to: string) => (to ? `/${roleDef.slug}/${to}` : `/${roleDef.slug}`);
  const activeItem = items.find((n) => pathFor(n.to) === location.pathname);
  const pageTitle = activeItem?.label ?? "Dashboard";

  // Close the mobile drawer on navigation.
  useEffect(() => setOpen(false), [location.pathname]);

  const sidebar = (
    <div className="flex h-full flex-col bg-gradient-to-b from-navyDeep to-navy text-white">
      <Link to={`/${roleDef.slug}`} className="flex items-center gap-3 px-5 py-5">
        <Logo size={36} className="ring-2 ring-white/15" />
        <div className="leading-tight">
          <div className="text-sm font-semibold">Advantage Pro</div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-white/50">
            Learning Management
          </div>
        </div>
      </Link>

      <div className="mx-4 mb-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3">
        <div className="text-[10px] uppercase tracking-wider text-white/45">Current workspace</div>
        <div className="mt-1 flex items-center justify-between">
          <span className="text-sm font-medium">{roleDef.label}</span>
          <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_0_3px_rgba(52,211,153,0.18)]" />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {GROUP_ORDER.map((g) => {
          const groupItems = items.filter((n) => n.group === g);
          if (groupItems.length === 0) return null;
          return (
            <div key={g} className="mb-2">
              <div className="px-3 pb-1 pt-3 text-[10px] font-medium uppercase tracking-wider text-white/35">
                {g}
              </div>
              {groupItems.map(({ to, label, Icon }) => {
                const active = location.pathname === pathFor(to);
                return (
                  <Link
                    key={label}
                    to={pathFor(to)}
                    className={cn(
                      "relative mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                      active ? "text-white" : "text-white/65 hover:bg-white/5 hover:text-white",
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="ap-nav-active"
                        className="absolute inset-0 rounded-lg bg-white/12 ring-1 ring-inset ring-white/10"
                        transition={{ type: "spring", stiffness: 380, damping: 32 }}
                      />
                    )}
                    <Icon size={17} className="relative z-10 shrink-0" aria-hidden />
                    <span className="relative z-10 truncate">{label}</span>
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-4 py-3">
        <div className="flex items-center gap-3">
          <Avatar name={name} tone="brand" size={36} />
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-medium">{name}</div>
            <div className="truncate text-[11px] text-white/45">{user?.email || roleDef.label}</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-appbg">
      {roleDef.value === "student" && <EngagementPrompts />}

      <aside className="hidden w-64 shrink-0 md:block">
        <div className="fixed inset-y-0 left-0 w-64 shadow-sidebar">{sidebar}</div>
      </aside>

      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-40 md:hidden">
            <motion.div
              className="absolute inset-0 bg-navyDeep/50 backdrop-blur-sm"
              onClick={() => setOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.aside
              className="absolute inset-y-0 left-0 w-64"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
            >
              {sidebar}
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col md:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-brdr bg-surface/85 px-4 backdrop-blur md:px-8">
          <div className="flex items-center gap-3">
            <button
              className="rounded-lg p-2 text-muted hover:bg-sky md:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div className="leading-tight">
              <div className="text-[11px] uppercase tracking-wider text-muted">
                Workspace / {roleDef.label}
              </div>
              <div className="text-base font-semibold text-ink">{pageTitle}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden rounded-full bg-sky px-3 py-1 text-xs font-medium text-navy sm:inline">
              {roleDef.label}
            </span>
            <NotificationBell />
            <div className="relative">
              <button
                onClick={() => setMenuOpen((v) => !v)}
                className="flex items-center gap-2 rounded-full border border-brdr bg-surface py-1 pl-1 pr-2 hover:bg-sky"
              >
                <Avatar name={name} size={30} />
                <span className="hidden text-sm font-medium text-ink sm:inline">{name}</span>
                <ChevronDown size={15} className="text-muted" />
              </button>
              <AnimatePresence>
                {menuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                    <motion.div
                      initial={{ opacity: 0, y: 6, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 4, scale: 0.98 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 z-20 mt-2 w-52 rounded-xl border border-brdr bg-surface p-1.5 shadow-lift"
                    >
                      <div className="px-3 py-2">
                        <div className="truncate text-sm font-medium text-ink">{name}</div>
                        <div className="truncate text-xs text-muted">{user?.email}</div>
                      </div>
                      <Link
                        to={`/${roleDef.slug}/change-password`}
                        onClick={() => setMenuOpen(false)}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-sky"
                      >
                        <KeyRound size={15} className="text-muted" /> Change password
                      </Link>
                      <button
                        onClick={() => void logout()}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-sky"
                      >
                        <LogOut size={15} className="text-muted" /> Sign out
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8">
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="hidden"
            animate="show"
            className="mx-auto max-w-6xl"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
}

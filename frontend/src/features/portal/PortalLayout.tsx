import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Award,
  BarChart3,
  BookOpen,
  CalendarCheck,
  ChevronDown,
  ClipboardList,
  Download,
  Eye,
  FileText,
  Gift,
  KeyRound,
  LayoutDashboard,
  Link2,
  LogOut,
  type LucideIcon,
  Menu,
  MessagesSquare,
  PlayCircle,
  Radio,
  Settings,
  ShieldCheck,
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
import { WelcomePrompts } from "../welcome/WelcomePrompts";

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
const FORUM = role("tech_support", "faculty", "student");
const MONITOR = role("tech_support");
const DEVICES = role("mis", "tech_support", "faculty");
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
  {
    to: "courses",
    label: "Courses",
    Icon: BookOpen,
    roles: role("super_admin"),
    group: "People & batches",
  },
  {
    to: "profile",
    label: "My skills",
    Icon: Sparkles,
    roles: role("faculty"),
    group: "People & batches",
  },
  {
    to: "enrolment",
    label: "Enrolment",
    Icon: UserPlus,
    roles: ADMIN_MIS,
    group: "People & batches",
  },
  {
    to: "goodies",
    label: "Addresses & goodies",
    Icon: Gift,
    roles: ADMIN_MIS,
    group: "People & batches",
  },
  {
    to: "staff",
    label: "Staff",
    Icon: UserCog,
    roles: role("super_admin"),
    group: "People & batches",
  },
  { to: "content", label: "Content", Icon: Video, roles: CONTENT, group: "Learning" },
  { to: "videos", label: "Videos", Icon: PlayCircle, roles: role("student"), group: "Learning" },
  { to: "tests", label: "Tests", Icon: ClipboardList, roles: TESTS, group: "Learning" },
  { to: "tasks", label: "Tasks", Icon: FileText, roles: TASKS, group: "Learning" },
  { to: "live", label: "Live classes", Icon: Radio, roles: LIVE, group: "Learning" },
  {
    to: "calendar",
    label: "Calendar",
    Icon: CalendarCheck,
    roles: role("student"),
    group: "Learning",
  },
  { to: "attendance", label: "Attendance", Icon: CalendarCheck, roles: ATTEND, group: "Tracking" },
  { to: "performance", label: "Performance", Icon: BarChart3, roles: ATTEND, group: "Tracking" },
  { to: "forum", label: "Forum", Icon: MessagesSquare, roles: FORUM, group: "Tracking" },
  { to: "monitor", label: "Doubt monitor", Icon: Eye, roles: MONITOR, group: "Tracking" },
  { to: "activity", label: "Activity", Icon: Activity, roles: ACTIVITY, group: "Tracking" },
  {
    to: "certificate",
    label: "Certificate",
    Icon: Award,
    roles: role("student"),
    group: "Completion",
  },
  {
    to: "certificates",
    label: "Certificates",
    Icon: Award,
    roles: role("admin", "mis"),
    group: "Completion",
  },
  { to: "engagement", label: "Engagement", Icon: Sparkles, roles: ADMIN_MIS, group: "Completion" },
  { to: "devices", label: "Devices", Icon: Smartphone, roles: DEVICES, group: "Operations" },
  {
    to: "utility-links",
    label: "Utility links",
    Icon: Link2,
    roles: role("mis"),
    group: "Operations",
  },
  {
    to: "escalations",
    label: "Escalations",
    Icon: TriangleAlert,
    roles: ESCALATIONS,
    group: "Operations",
  },
  { to: "reports", label: "Reports", Icon: Download, roles: REPORTS, group: "Operations" },
  {
    to: "channels",
    label: "Channels",
    Icon: Settings,
    roles: role("super_admin"),
    group: "Operations",
  },
  {
    to: "permissions",
    label: "Permissions",
    Icon: KeyRound,
    roles: role("super_admin"),
    group: "Operations",
  },
  {
    to: "feedback",
    label: "Message management",
    Icon: MessagesSquare,
    roles: role("student"),
    group: "Completion",
  },
  {
    to: "feedback",
    label: "Feedback inbox",
    Icon: MessagesSquare,
    roles: role("super_admin"),
    group: "Operations",
  },
];

const GROUP_ORDER = [
  "Overview",
  "People & batches",
  "Learning",
  "Tracking",
  "Completion",
  "Operations",
];

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

  // Keyboard path for closing the profile menu (the backdrop is pointer-only).
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const sidebar = (
    <div className="ap-sidebar flex h-full flex-col border-r border-white/60 text-ink">
      <Link to={`/${roleDef.slug}`} className="flex items-center gap-3 px-5 py-5">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white shadow-card ring-1 ring-black/5">
          <Logo size={40} />
        </span>
        <div className="leading-tight">
          <div className="text-[15px] font-semibold text-navy">Advantage Pro</div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted">
            Learning Management
          </div>
        </div>
      </Link>

      <div className="mx-4 mb-2 rounded-2xl border border-white/70 bg-white/60 px-4 py-3 shadow-card backdrop-blur">
        <div className="text-[10px] uppercase tracking-wider text-muted">Current workspace</div>
        <div className="mt-1 flex items-center justify-between">
          <span className="text-sm font-semibold text-navy">{roleDef.label}</span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-success">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_0_3px_rgba(16,185,129,0.18)]" />
            Online
          </span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {GROUP_ORDER.map((g) => {
          const groupItems = items.filter((n) => n.group === g);
          if (groupItems.length === 0) return null;
          return (
            <div key={g} className="mb-1.5">
              <div className="px-3 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wider text-muted/80">
                {g}
              </div>
              {groupItems.map(({ to, label, Icon }) => {
                const active = location.pathname === pathFor(to);
                return (
                  <Link
                    key={label}
                    to={pathFor(to)}
                    className={cn(
                      "group relative mb-0.5 flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm transition-all",
                      active
                        ? "text-brand-strong"
                        : "text-ink/70 hover:translate-x-[3px] hover:text-navy",
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="ap-nav-active"
                        className="absolute inset-0 rounded-xl bg-white shadow-card ring-1 ring-black/5"
                        transition={{ type: "spring", stiffness: 380, damping: 32 }}
                      />
                    )}
                    <span
                      className={cn(
                        "relative z-10 flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
                        active
                          ? "bg-brand text-white shadow-sm"
                          : "bg-white/70 text-navy/70 group-hover:bg-white group-hover:text-brand-strong",
                      )}
                    >
                      <Icon size={16} aria-hidden />
                    </span>
                    <span className="relative z-10 truncate font-medium">{label}</span>
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      <div className="border-t border-white/70 px-4 py-3">
        <div className="flex items-center gap-3">
          <Avatar name={name} size={38} />
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-semibold text-navy">{name}</div>
            <div className="truncate text-[11px] text-muted">{user?.email || roleDef.label}</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="ap-appbg flex min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded-xl focus:bg-navy focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>
      {roleDef.value === "student" && <WelcomePrompts />}
      {roleDef.value === "student" && <EngagementPrompts />}

      <aside className="hidden w-64 shrink-0 md:block">
        <div className="fixed inset-y-0 left-0 w-64 shadow-[2px_0_24px_rgba(15,31,58,0.05)]">
          {sidebar}
        </div>
      </aside>

      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-40 md:hidden">
            <motion.div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
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

      <div className="flex min-w-0 flex-1 flex-col">
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
                    <div
                      aria-hidden="true"
                      className="fixed inset-0 z-10"
                      onClick={() => setMenuOpen(false)}
                    />
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
                      {roleDef.value !== "student" && (
                        <Link
                          to={`/${roleDef.slug}/security`}
                          onClick={() => setMenuOpen(false)}
                          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-sky"
                        >
                          <ShieldCheck size={15} className="text-muted" /> Two-factor authentication
                        </Link>
                      )}
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

        <main id="main-content" className="flex-1 px-5 py-6 md:px-8 md:py-8">
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="hidden"
            animate="show"
            className="w-full max-w-[1400px]"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
}

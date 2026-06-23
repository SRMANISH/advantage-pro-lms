export interface RoleDef {
  /** URL segment for the login + portal route. */
  slug: string;
  /** Backend role value (matches core.roles.Role). */
  value: string;
  label: string;
  tagline: string;
}

/** The seven roles, each with its own login page (role-bound). */
export const ROLES: RoleDef[] = [
  { slug: "student", value: "student", label: "Student", tagline: "Your batch, in one place." },
  {
    slug: "faculty",
    value: "faculty",
    label: "Faculty",
    tagline: "Teach, grade, and guide your batches.",
  },
  { slug: "admin", value: "admin", label: "Admin", tagline: "Run day-to-day operations." },
  { slug: "mis", value: "mis", label: "MIS Executive", tagline: "Monitor sessions and escalations." },
  { slug: "counselor", value: "counselor", label: "Counselor", tagline: "Attendance and follow-up." },
  {
    slug: "tech-support",
    value: "tech_support",
    label: "Tech Support",
    tagline: "Keep the doubt forum moving.",
  },
  {
    slug: "super-admin",
    value: "super_admin",
    label: "Super Admin",
    tagline: "Full control and settings.",
  },
];

/** Map a backend role value to its route slug (e.g. tech_support -> tech-support). */
export function slugForRole(value: string): string {
  return ROLES.find((r) => r.value === value)?.slug ?? "";
}

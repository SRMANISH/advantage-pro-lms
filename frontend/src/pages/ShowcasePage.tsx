import { Link } from "react-router-dom";

import { ROLES } from "../app/roles";
import { Badge, Button, Card, Input, Logo } from "../design-system";

const SWATCHES = [
  { name: "Brand", hex: "#00A0E0", className: "bg-brand" },
  { name: "Brand strong", hex: "#007AB0", className: "bg-brand-strong" },
  { name: "Sky", hex: "#E6F6FD", className: "bg-sky" },
  { name: "Navy", hex: "#163A8C", className: "bg-navy" },
  { name: "Violet", hex: "#6E2EA0", className: "bg-violet" },
];

export function ShowcasePage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8 flex items-center justify-between">
        <Logo />
        <Badge>Module 0 · design system</Badge>
      </header>

      <h1 className="mb-1 text-2xl font-medium text-ink">Advantage Pro LMS</h1>
      <p className="mb-8 text-sm text-muted">
        Light-blue &amp; white design system — the foundation every portal is built on.
      </p>

      <section className="mb-8">
        <h2 className="mb-3 text-base font-medium text-ink">Palette</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {SWATCHES.map((s) => (
            <Card key={s.name} className="p-3">
              <div className={`mb-2 h-12 w-full rounded-lg ${s.className}`} />
              <div className="text-sm font-medium text-ink">{s.name}</div>
              <div className="text-xs text-muted">{s.hex}</div>
            </Card>
          ))}
        </div>
      </section>

      <section className="mb-8 grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Buttons</h2>
          <div className="flex flex-wrap gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="soft">Soft</Button>
            <Button variant="ghost">Ghost</Button>
          </div>
        </Card>
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Inputs &amp; badges</h2>
          <Input placeholder="Type here…" className="mb-3" />
          <div className="flex gap-2">
            <Badge>Active</Badge>
            <Badge>Draft</Badge>
            <Badge>Completed</Badge>
          </div>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 text-base font-medium text-ink">Role login pages</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {ROLES.map((role) => (
            <Link
              key={role.slug}
              to={`/login/${role.slug}`}
              className="rounded-xl border border-brdr bg-surface px-4 py-3 text-sm font-medium text-brand-strong transition hover:bg-sky"
            >
              {role.label}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

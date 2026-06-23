# Advantage Pro LMS — Design Plan (UI/UX)

> How the final product looks and behaves. Pairs with `BUILD_PLAN.md` (architecture/modules).
> Visual language: **light blue & white**, anchored on the Advantage Pro / Vectra Technosoft brand.

---

## 1. Brand palette (sampled from the logo)

Sampled from `frontend/src/assets/logo.jpeg`.

| Token | Hex | Use |
|-------|-----|-----|
| Brand azure | `#00A0E0` | Accents, active state, progress, highlights (logo "ADVANTAGE PRO") |
| Brand strong | `#007AB0` | Primary buttons, hover (AA on white) |
| Sky tint | `#E6F6FD` | Light-blue surfaces, active backgrounds, chips |
| Navy | `#163A8C` | Headings, sidebar, strong text, links (logo ring/tagline) |
| Violet (accent) | `#6E2EA0` | Sparing accent (badges, highlights — from emblem) |
| Red (alert) | `#DD1F26` | Errors, overdue/late, destructive — sparing (logo "since 1998") |
| Surface | `#FFFFFF` | Cards, panels |
| App background | `#F4FAFE` | Page background |
| Border | `#D6EBF8` | Dividers, card borders |
| Text / muted | `#0F1F3A` / `#5A6982` | Body text / secondary |

- Semantic: success `#1E8E5A`, warning `#B9770E`, info = brand blue.
- All combinations meet **WCAG AA**. Tokens defined once; theme is **swappable / white-label ready** (dynamic).
- Real logo file → `frontend/src/assets/logo.png`; shown on login + every portal header.

## 2. Typography & components
- **Type:** clean sans (Inter/system). Sizes: H1 22, H2 18, H3 16, body 14–16; two weights (regular/medium).
- **Look:** flat, white surfaces, soft 1px light-blue borders, gentle rounded corners (8–12px), generous whitespace, light-blue tinted (not heavy) buttons.
- **Component kit (built once):** buttons, inputs, selects, cards, metric cards, tables, tabs, badges/pills, modals, toasts, avatars, progress bars, empty/loading/error states, file drop-zone.

## 3. Navigation model
- **Separate login page per role** (own URL each): `/login/student`, `/login/faculty`, `/login/admin`, `/login/mis`, `/login/counselor`, `/login/tech-support`, plus a discreet Super Admin URL. Same brand layout, role-labelled. An account can authenticate **only** through its own role's page — correct credentials on the wrong page are refused. Per-page rate-limiting; role existence not leaked.
- **App shell:** left **icon nav rail** (role-specific items) + **top header** (logo, page title, search where useful, notification bell, avatar/menu). Content area = white cards on the light-blue page background.
- Breadcrumb inside batch sub-views (Batch → Videos / Tests / Tasks / Attendance / Forum).

## 4. Information architecture (sitemap)

```
Login — one dedicated page/URL per role (role-bound) → that role's isolated portal:
├─ Student        Dashboard · Videos · Tests · Tasks · Live classes · Forum · Attendance · Certificate
├─ Faculty        Dashboard · My batches · Upload video/notes · Tests · Tasks · Forum · Performance
├─ Admin          Dashboard · Batches · Enrolment/Import · Live classes · Users · Reports
├─ MIS Executive  Monitoring dashboard · Batches · Sessions · Tests/attendance health · Escalations
├─ Counselor      Attendance review · Absence follow-up · Performance reports
├─ Tech Support   Forum monitor (only) · Unanswered-doubt reminders
└─ Super Admin    Overview · Staff & roles · RBAC/permissions · Settings · Audit log · Batch delete
```

## 5. Screen-by-screen layout

**Login (one page per role)** — centered split card: left brand panel (logo, "Networking with success", since 1998) on sky tint; right form (email, password, sign in) **labelled with the role** ("Counselor sign in", "Tech Support sign in", …). Each role has its own URL and is role-bound — an account can only sign in through its own page. Student setup flow = link → email OTP → phone OTP → set password, as a 3-step stepper.

**Student dashboard** — metric cards (attendance %, videos watched, avg score, tasks done); "upcoming live class" card with Join; "continue watching" with resume bar; recent activity feed.

**Student video player (signature)** — in-frame player with a **moving diagonal watermark** (name + student ID + timestamp), **no download**, resume indicator; below: watched-% bar, view-only notes, and the **upsell prompt** ("colleagues at your company completed the next course…"); "ask a doubt" action.

**Faculty dashboard** — metric cards (batches, pending grading, open doubts, new-device alerts); "your batches" grid; "needs attention" (grading queue + doubts); quick actions (upload video, create test/task). Device-change approval appears as an in-context request during a live class.

**Admin dashboard** — metric cards (active batches, students, imports, today's live classes); **student import wizard** (drop file → row-by-row validation → all-or-nothing confirm); **schedule live class** mini-form; recent activity.

**MIS** — same powers as Admin but a monitoring lens: health tiles (sessions running, attendance captured, tests done) + escalation inbox (missed-class / incomplete-test alerts).

**Counselor** — attendance review table per batch (who missed which date), one-click absence message using a standard script; performance/attendance reports only.

**Tech Support** — forum-only view: incoming doubts, time-waiting, and "remind faculty" action (~3h target). Nothing else visible.

**Super Admin** — overview + staff/role management + **dynamic settings** (business thresholds, RBAC matrix, notification templates, theme tokens) + append-only **audit log**.

## 6. How "dynamic" shows in the UI
A **Settings** area (Super Admin) exposes, with no redeploy: video attendance threshold (80%), absence rule (50%), doubt window (~3h), OTP/link expiry, reminder timings, the **RBAC matrix** (roles × permissions toggles), editable **notification templates**, and **theme tokens** (white-label). Dashboards and nav are data-driven per role.

## 7. States, responsive & accessibility
- Every list/table has explicit **loading, empty, and error** states.
- **Responsive:** rail collapses to a drawer on small screens; cards reflow to single column; tables scroll/condense.
- **Accessibility:** WCAG AA contrast, full keyboard nav, visible focus rings, ARIA labels, semantic landmarks, reduced-motion respected (watermark motion subtle).

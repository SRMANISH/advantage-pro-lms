# Local audit report

A full local pass over the codebase: dead code, duplication, every endpoint against its role
gating and its test coverage, N+1 and algorithm review, and structure. Done with tooling
(vulture, knip, jscpd, an AST loop-query scan, a URL/permission/test cross-reference) rather
than by eye, so the conclusions are reproducible.

**Headline:** the codebase is in good shape. The dead-code and duplication sweeps came back
nearly empty, and the authorization model has no holes. The one real category of finding was
**test coverage** — four endpoints with genuine behaviour and zero tests, now closed.

**Verification after fixes:** 506 backend tests (was 497), 50 frontend, 12/12 Playwright.
ruff / black / mypy / eslint / tsc all clean.

---

## What was checked, and what it found

| Area | Tool / method | Result |
|---|---|---|
| Backend dead code | `vulture` @ 80% | Near-zero — 3 interface params + 1 dead test arg |
| Frontend dead code | `knip` | 0 unused files, 0 unused deps, 3 unused components |
| Duplication | `jscpd` | 0.5% — 5 clones of 11–19 lines, all natural JSX |
| Authorization | URL × permission-class × matrix cross-reference | **No holes** |
| Test coverage | endpoint × test cross-reference | **4 untested endpoints** → fixed |
| N+1 / algorithms | AST scan for queries-in-loops | No request-path N+1s |

---

## Bugs and required fixes

Ranked by consequence.

### FIXED — 4 endpoints with real behaviour and no test *(medium)*

Found by enumerating all 89 API views and cross-referencing which are exercised by any test.
Four were not, and all four do something worth testing:

| Endpoint | View | Why it mattered |
|---|---|---|
| `POST /video-access/restore/` | `RestoreVideoAccessView` | **State-changing** — deletes revocation rows, re-granting video access. Its *revoke* counterpart was tested; *restore* was not. Asymmetric coverage of a matrix-gated pair is exactly where a regression hides |
| `POST /auth/password/resend/` | `ForgotPasswordResendView` | Re-issues an OTP and increments the resend cap — the abuse control on the reset flow |
| `GET /forum/batches/` | `ForumBatchesView` | Role-scoped read: Tech Support sees all, faculty their own, students their enrolled, MIS none |
| `GET /engagement/reports/google-review/` | `GoogleReviewReportView` | Whole-cohort review status — must be Admin/MIS only |

**Fix.** `tests/test_coverage_gaps.py`, 9 tests covering the happy path, the role gate, and the
404/refusal edges for each.

**One caught in the act.** The resend test I first wrote passed *vacuously* — it plumbed the
flow token through the session, but the view reads it from the request body, so the test
sailed through the invalid-session branch without ever resending. It now sends the token where
the view looks and asserts `resend_count` actually incremented. Worth flagging because it is
the same failure mode as two tests found earlier in this work: a green test that exercises
nothing.

### FIXED — dead test argument *(trivial)*

`tests/test_retention.py` had `def test_...(django_assert_num_queries=None)` — an unused
parameter default, the only genuine dead code vulture found. Removed.

### NOTED — mild N+1 in a cron job *(low, not fixed)*

`engagement/services.py::remind_next_plan` does `CourseNextPlan.objects.filter(student=student)
.exists()` once per completed-course student. It is a scheduled job, bounded by the number of
graduates, not a request path — so it is a real N+1 but a harmless one. Collapsible to a single
`_completed_students().exclude(next_plan__isnull=False)` if the graduate count ever grows.
Left as-is because the rewrite would touch the `_completed_students` contract for no current
benefit.

---

## Findings that are *not* bugs, but worth knowing

### The Modal accessibility work landed on an unused component

`Modal` has **zero references** anywhere in the app — nothing renders it. The focus-trapping,
Escape handling and focus restoration added to it in the previous phase are correct and tested,
but they are on a design-system primitive that no page uses. `PageTransition` and `Tabs` are
the same: exported, never rendered.

This is a judgement call, not a defect. A design system legitimately keeps primitives ahead of
use. But if the intent is "remove every redundant thing", these three components (~180 lines)
are the candidates — with the caveat that `Modal` is genuinely good and you may want it the
first time a confirm-dialog is needed. **Recommendation: keep them, they are library surface,
not dead application code.** Listed so the decision is yours.

### A few redundant barrel re-exports

`design-system/index.ts` re-exports `toast`, `fade` and a couple of others that are only ever
imported directly from their source module. Harmless (the underlying symbols are used), purely
cosmetic. Not worth a commit on their own.

### Duplication is real but not worth extracting

The five `jscpd` clones are 11–19 lines of structurally-similar JSX — a progress ring, two
table-row shapes, a two-step form. Extracting them would trade a little repetition for a lot of
indirection and read worse. The one arguably worth it (`SetupPage.tsx:136` vs `:153`, the two
OTP steps) is a local pattern a future edit can consolidate in place.

---

## What came back clean

Stated explicitly, because "we checked and found nothing" is a result.

- **Authorization.** Every view gated only by `IsAuthenticated` was verified to either
  self-scope on `request.user` (the `*/me` reads, dashboard, change-password) or apply a manual
  matrix check inside the handler. `UserStatusView` — which suspends accounts and carries only
  `IsAuthenticated` at the class level — computes the required action from the *target's* role
  and calls `can(request.user.role, action)`, returning 403 otherwise. `UtilityLinksView` gates
  its POST behind `UtilityManageRoles` via `get_permissions`. No endpoint trusts the client for
  a scoping decision.
- **Request-path performance.** Every ORM-query-inside-a-loop the AST scan found is in a cron
  job or the bulk importer, bounded and mostly set-based. The hot reads (dashboard, performance
  board) are already grouped into a handful of queries. No per-row query on a request path.
- **Backend dead code.** The three `vulture` hits at high confidence are all required interface
  parameters — `expires_in` on the storage-adapter protocol (used by a signed-URL adapter),
  `auto_schema` on the drf-spectacular extension. Not removable.
- **Dependencies.** No unused packages either side. No unused source files.

---

## The pattern across this audit and the work before it

The defects in this codebase have consistently been **invisible from reading it** and visible
only from executing something:

- a Playwright spec that passed because a dataset was small,
- a focus test that passed because it raced a `requestAnimationFrame`,
- a `format:check` gate that had been failing since it was added,
- and here, a coverage test that passed without exercising its endpoint.

The code that *looks* right largely *is* right — the dead-code, duplication, authorization and
N+1 sweeps confirm that. The residual risk is concentrated in the gap between "the tests pass"
and "the tests would catch a regression", which is why the fix in this pass was tests, and why
one of those tests had to be fixed for testing nothing before it counted.

The remaining unexamined areas are unchanged from `docs/PRE_PRODUCTION_CHECKLIST.md` § Phase 5:
timezone/day-boundary behaviour, broader frontend accessibility beyond the modal, and a
deliberate pass over test *quality* rather than test *count*.

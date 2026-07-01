# Advantage Pro LMS — Demo & Feature Testing Guide

A step-by-step script to demonstrate **every feature for every role** and prove it works.
All data below comes from `python manage.py seed_demo` (idempotent). Password for **all**
demo accounts is **`Demo!passLMS1`**.

---

## 0. One-time setup

```cmd
:: 1) seed demo data (idempotent — safe to re-run)
cd /d "C:\Users\Manish SR\Downloads\Advantage Pro LMS\backend" && .venv\Scripts\activate.bat && python manage.py seed_demo

:: 2) Terminal 1 — backend API
cd /d "C:\Users\Manish SR\Downloads\Advantage Pro LMS\backend" && .venv\Scripts\activate.bat && python manage.py runserver 8000

:: 3) Terminal 2 — frontend
cd /d "C:\Users\Manish SR\Downloads\Advantage Pro LMS\frontend" && npm run dev
```

Open **http://localhost:5173**. Keep **Terminal 1 (backend) visible** — OTP codes and
email/SMS/WhatsApp messages print there in dev (console adapters).

> **Login is role-bound.** Each role signs in through its own page; the server rejects an
> account used on the wrong portal. Use the exact URLs below.

---

## 1. Accounts & portals

| Role | Login ID | Password | Email | Portal URL |
|---|---|---|---|---|
| Student | `student1` | `Demo!passLMS1` | student1@example.com | `/login/student` |
| Faculty | `faculty1` | `Demo!passLMS1` | faculty1@example.com | `/login/faculty` |
| Admin | `admin1` | `Demo!passLMS1` | admin1@example.com | `/login/admin` |
| MIS Executive | `mis1` | `Demo!passLMS1` | mis1@example.com | `/login/mis` |
| Counsellor | `counselor1` | `Demo!passLMS1` | counselor1@example.com | `/login/counselor` |
| Tech Support | `techsupport1` | `Demo!passLMS1` | techsupport1@example.com | `/login/tech-support` |
| Super Admin | `superadmin1` | `Demo!passLMS1` | superadmin1@example.com | `/login/super-admin` |

**Demo students** (enrolled in batch **FS-DEMO**, all password `Demo!passLMS1`):
`S101`–`S108` (Asha Rao, Ravi Kumar, Meena Iyer, Karthik Nair, Sneha Patel, Arjun Menon,
Divya Suresh, Rahul Verma), emails `s101@example.com` … `s108@example.com`.

From the landing page you can reach every portal: Student / Faculty / Admin / Super Admin as
buttons, plus **MIS / Counsellor / Tech Support** under "Staff portals".

---

## 2. Feature verification matrix (what to prove, per role)

Legend: ✅ works with seed data as-is · ⚙️ needs a one-step setup during the demo (noted).

### Student — `student1`
| Feature | How to demonstrate | Expected result |
|---|---|---|
| Login (role-bound) | Sign in at `/login/student` | Lands on the student dashboard |
| LinkedIn follow popup | Appears right after login | "Follow us on LinkedIn" modal; **Later** dismisses for the session, **Confirm** stops it |
| Dashboard | View home | KPI cards count up (Attendance, Pending tasks, Upcoming tests, Streak), activity area chart, "Up next" |
| Videos + watermark | **Videos** → Watch | Player opens with a moving **watermark of the student's name** ✅ *(seed videos are placeholder files — flow works, no real footage)* |
| Tests | **Tests** → Take an "open" test → Submit | Auto-graded, shows score instantly |
| Tasks | **Tasks** → type/attach → Submit | Submitted state; late tasks flagged; graded ones show score/feedback |
| Live classes | **Live classes** → Join & check-in | Opens meeting link; attendance check-in recorded |
| Attendance | **Attendance** | Login-based %, present/total days |
| Performance | **Performance** | Overall %, rank, per-category (tests/tasks/videos/attendance) |
| Forum | **Forum** → post a doubt | Thread appears; faculty/TS can reply |
| Certificate | **Certificate** | ⚙️ empty until the batch is **Completed** (see §3) then enter a Certificate ID |
| Change password | Profile menu → Change password | Success toast; can sign in with the new password |
| Forgot password | Logout → **Forgot password?** | Two-step: email OTP → phone OTP → reset (codes in backend console) |

### Faculty — `faculty1`
| Feature | How to demonstrate | Expected |
|---|---|---|
| Dashboard | Sign in `/login/faculty` | Batches, students, unanswered doubts, to-grade, activity trend |
| Batches (view) | **Batches** | Sees assigned batches (no Create/Assign — that's Admin) |
| Upload video | **Content** → Upload class video | Video added to batch |
| Upload notes | **Content** → Upload note | Note added |
| Create test | **Tests** → New test → add questions | Test created (MIS can too; Admin cannot) |
| Create task | **Tasks** → New task (deadline type) | Task created |
| Grade submissions | **Tasks** → open task → Grade | Score + feedback saved; student notified |
| Schedule live class | **Live classes** → Schedule + notify | Class appears for students; reminders queued |
| Cancel live class | **Live classes** → Cancel | Students notified; class marked cancelled |
| Reply / resolve doubt | **Forum** → Reply / Mark resolved | Thread status → answered/resolved |
| Activity feed | **Activity** | Sees own actions + own-batch activity |
| Approve device change (in class) | See §3 device flow | Only allowed while a live class is active |

### Admin — `admin1`
| Feature | How to demonstrate | Expected |
|---|---|---|
| Dashboard | Sign in `/login/admin` | Institute totals, batch-state donut, certificate-pending, platform trend |
| Create batch | **Batches** → New batch | Batch created (MIS cannot) |
| Assign faculty | **Batches** → Assign faculty dropdown | Faculty assigned (Faculty cannot) |
| Batch lifecycle | **Batches** → Activate / Complete | Draft→Active→Completed; **Complete closes video access** |
| Import students | **Enrolment** → drag CSV → Validate → Confirm | All-or-nothing validation; row errors listed; clean file imports |
| Add Counsellor | **Staff** → role = Counsellor → Create | New Counsellor (Admin can only create Counsellor) |
| Close course video access | (with MIS) after completion | Students lose video access |
| Reports | **Reports** → pick batch → download CSV | Students / attendance / performance CSVs |

### MIS Executive — `mis1`
| Feature | How to demonstrate | Expected |
|---|---|---|
| Dashboard | Sign in `/login/mis` | Totals + pending device requests + certificate-pending |
| Import students | **Enrolment** | MIS can import (not create batches) |
| Upload notes / MCQ | **Content** / **Tests** | Allowed (videos are Faculty-only) |
| Attendance follow-up | **Attendance** → daily roster → set follow-up status | Absentees listed; status Pending/Contacted/… |
| Certificate follow-up | **Certificates** | ⚙️ after a batch completes: pending list + weekly reminders + status |
| Approve device change (outside class) | See §3 | MIS approves when no class is active |
| Revoke / close video access | **Content** (MIS) | Individual revoke + course-end closure |
| Activity feed | **Activity** | Full platform activity |
| Escalations | **Escalations** → Run checks | Sends incomplete-test + 50%-attendance alerts |

### Counsellor — `counselor1`
| Feature | How to demonstrate | Expected |
|---|---|---|
| Dashboard | Sign in `/login/counselor` | Active students, logged-in today, absentees today, trend |
| Attendance review | **Attendance** → daily roster | Sees who logged in / who didn't |
| Absentee follow-up | Set follow-up status / send message | Status recorded; student notified |
| Performance (read) | **Performance** | Read-only follow-up view |
| Scope check | Try other nav | Only attendance/performance-related tools appear |

### Tech Support — `techsupport1`
| Feature | How to demonstrate | Expected |
|---|---|---|
| Dashboard | Sign in `/login/tech-support` | Open / unanswered / overdue / resolved + forum-status chart |
| Doubt monitor | **Doubt monitor** | Unanswered doubts; overdue flag past the SLA window |
| Answer a doubt | **Forum** → open thread → Reply | Reply posts; thread → answered |
| Escalate a doubt | **Forum** → Escalate | Faculty notified; status → escalated |
| Remind faculty | **Doubt monitor** → Remind faculty | Faculty gets a reminder |
| Scope check | Try other nav | Forum + monitor only — nothing else |

### Super Admin — `superadmin1`
| Feature | How to demonstrate | Expected |
|---|---|---|
| Dashboard | Sign in `/login/super-admin` | Institute overview |
| Staff accounts | **Staff** → create any staff role | SA can create Admin/MIS/Counsellor/Tech Support/Faculty |
| Channels | **Channels** → send test message | Test via the email/SMS/WhatsApp adapter (logs to backend console) |
| Delete batch | **Batches** | Permanent delete (Super Admin) |
| Locked-out check | Note the nav | **No** Activity, no video revoke, no notes/MCQ upload, no batch-create, no live scheduling |

---

## 3. Cross-cutting flows (the ones worth staging live)

**A. Enrolment → two-step setup → first login**
1. Admin → **Enrolment** → download template, add one new row with a fresh Registration ID → drag in → **Validate** → **Confirm import**.
2. On the new student's row click **Setup link** → open it (or check the backend console for the setup email + link).
3. Student opens link → enter **email OTP** (backend console) → **phone OTP** (console) → set password → account becomes Active.
4. Admin + MIS get a first-login alert.

**B. Doubt → answer → escalate**
Student posts a doubt (Forum) → Tech Support answers or **Escalates** → Faculty notified → Faculty resolves.

**C. Device policy (in-class vs outside-class)**
1. As a student, open an **incognito window** (fresh device fingerprint) and sign in → **blocked**, a device-change request is created.
2. **Outside class:** MIS → **Devices** → Approve (works because no class is active).
3. **In class:** Faculty schedules a live class for *now* (Live classes → time = now), then Faculty → **Devices** → Approve (only allowed during the active class).

**D. Course completion → certification + reviews**
1. Admin → **Batches** → **Complete** the FS-DEMO batch. *(This also closes video access.)*
2. Student now sees the **Certificate** page → enter a Certificate ID (stops reminders).
3. Student login now shows the **Google review** and **next-plan** popups.
4. MIS → **Certificates** → sees pending list + can send weekly reminders.

**E. Escalations & reminders (scheduled jobs, run manually in the demo)**
- MIS → **Escalations** → **Run checks** (incomplete tests + 50% attendance).
- Or from the backend terminal: `python manage.py send_absence_reminders`,
  `send_certificate_reminders`, `send_engagement_reminders`, `send_due_reminders`,
  `run_escalations`.

---

## 4. Recommended demonstration plan (the flow that tells a story)

Do it in this order — it mirrors a real student journey and shows each role's ownership.

1. **Landing + role portals** — show the login page, the rotating quote, and that every
   role has its own portal (Student…Super Admin).
2. **Admin sets up** (`admin1`): create a batch → assign `faculty1` → import a student list
   (show validation rejecting a bad row, then a clean import).
3. **Setup + login**: open the new student's setup link → email OTP → phone OTP → password
   (codes in the backend console). Then log in as that student.
4. **Student experience** (`student1`): LinkedIn popup → dashboard KPIs/chart → watch a video
   (watermark) → take a test → submit a task → post a doubt → check attendance/performance.
5. **Faculty** (`faculty1`): grade the task → reply/resolve the doubt → schedule a live class.
6. **Tech Support** (`techsupport1`): show the doubt monitor, answer/escalate, remind faculty.
7. **Counsellor + MIS** (`counselor1`, `mis1`): attendance daily roster → mark absentee
   follow-up → run escalations.
8. **Device policy**: incognito student login (blocked) → MIS approves outside class →
   (optional) Faculty approves during a live class.
9. **Completion** (`admin1`): complete the batch → student enters Certificate ID → Google
   review + next-plan popups → MIS certificate follow-up.
10. **Super Admin** (`superadmin1`): staff creation, Channels test message, and point out the
    features SA is intentionally locked out of.
11. **Reports**: Admin/MIS download the students / attendance / performance CSVs.

---

## 5. Notes & known demo limitations

- **OTP / email / SMS / WhatsApp** print to the **backend terminal** in dev (console
  adapters). Real providers are wired at deploy via `LMS_*_ADAPTER`.
- **Seed videos are placeholder files** — the player, watermark, progress and attendance-on-
  watch all work, but there's no real footage. Upload a real MP4 (Faculty → Content) to show
  actual playback.
- **Certification, Google review, and next-plan** need a **Completed** batch — complete
  FS-DEMO first (flow D).
- **LinkedIn / Google review links** use placeholder URLs until `VITE_LINKEDIN_URL` /
  `VITE_GOOGLE_REVIEW_URL` are set at deploy.
- Re-running `seed_demo` is safe; it keeps the demo batch current and tops up login
  attendance so dashboards stay populated.

# Advantage Pro LMS — Flow-by-Flow Demo Runbook

Detailed, scripted walkthroughs for **every flow**, using **different logins** so each
demo feels real and shows role ownership + scoping. Accounts, URLs and setup are in
[DEMO_GUIDE.md](DEMO_GUIDE.md). Password for **student1** is **`Adv123*`**; all others use **`Demo!passLMS1`**.

## How to run multi-actor flows
The app uses session cookies, so **you can only be one role per browser profile**. To run a
doubt/attendance flow "live" between two roles at once, open **separate windows**:

| Actor | Suggested window |
|---|---|
| Student (e.g. `S101`) | Chrome — normal window |
| Faculty `faculty1` | Chrome — **Incognito** |
| Tech Support `techsupport1` | Chrome — a **second profile** (or Edge/Firefox) |
| MIS `mis1` / Counsellor `counselor1` | another profile / browser |

Keep the **backend terminal visible** — OTPs, emails, SMS and WhatsApp all print there in dev.
Each student login also **records today's attendance**, which the later attendance flow uses.

---

## Flow 1 — Enrolment → two-step account setup → first login
**Actors:** `admin1` (import), a brand-new student.
**Proves:** all-or-nothing CSV validation + the two-step (email → phone) setup.

1. `admin1` → **Enrolment** → **Download template**.
2. Edit it: add a row with a **bad email** (e.g. `foo@`) → drag it in → **Validate** →
   shows the exact **row/field/problem** and rejects the whole file. *(Point out: nothing saved.)*
3. Fix the row (valid email, e.g. Registration ID `S200`, batch `FS-DEMO`, course `FS`,
   faculty `faculty1`) → drag in → **Validate** → "1 row valid" → **Confirm import**.
4. The new `S200` row shows **pending** → click **Setup link** → open it (or read the setup
   email in the backend terminal).
5. On the setup page: enter the **email OTP** (backend terminal) → then the **phone OTP** →
   set a password → account becomes **Active**.
6. `admin1` and `mis1` receive a **first-login alert** (check their notification bell).
7. Sign in as `S200` at `/login/student` with the new password.

---

## Flow 2 — Student daily experience (use several different students)
**Actors:** `S101`, `S102`, `S103` (log each in, separate windows or one after another).
**Proves:** per-student data + batch scoping + the login-attendance capture.

1. Sign in as **`S101`** → the **LinkedIn follow** popup appears → click **Open LinkedIn**
   then **I've followed** (or **Later**).
2. Dashboard: KPI cards **count up** (Attendance, Pending tasks, Upcoming tests, Streak),
   the **activity chart** draws in, "Up next" lists live classes.
3. **Videos** → Watch → note the **moving watermark = the student's own name/ID**.
4. **Forum** → shows only **FS-DEMO** doubts (batch scoping).
5. Sign out, sign in as **`S102`** → notice the numbers/KPIs are **different** (their own record).
6. Sign in as **`S103`** → same — proves every student sees only their own data.

> Each of these logins just wrote **today's attendance** for S101/S102/S103 — we'll use that
> in Flow 6.

---

## Flow 3 — Doubt forum: ask → answer → resolve
**Actors:** `S101` (asks), `faculty1` (answers), `techsupport1` (answers basic/tech).
**Proves:** the full doubt lifecycle + who can answer.

1. **`S101`** → **Forum** → **Ask a doubt** → batch `FS-DEMO`, title *"How do props work in React?"*,
   body → **Post doubt**. Status shows **open**.
2. **`faculty1`** (other window) → **Forum** → open that thread → **Reply** with an answer →
   status flips to **answered**. `S101` gets a **"New reply to your doubt"** notification.
3. Either **`faculty1`** or **`S101`** clicks **Mark resolved** → status **resolved**.
4. **`techsupport1`** → **Forum** → open a *technical* doubt (e.g. login/video issue) → **Reply**
   directly (Tech Support can answer, not just monitor).

## Flow 4 — Doubt: reminding faculty + escalation
**Actors:** `S104` (asks), `techsupport1` (monitors/reminds/escalates), `faculty1` (responds).
**Proves:** Tech Support keeps doubts moving; overdue + reminder + escalation.

1. **`S104`** → **Forum** → post a doubt and **leave it unanswered**.
2. **`techsupport1`** → **Doubt monitor** → the unanswered doubt is listed with **hours waiting**
   (it flags **overdue** once it passes the SLA window — default **3h**).
3. **`techsupport1`** → **Remind faculty** → `faculty1` gets a **"please respond"** reminder.
4. **`techsupport1`** → (in Forum) open the thread → **Escalate** → status **escalated**;
   `faculty1` gets a **"doubt escalated"** email + in-app alert.
5. **`faculty1`** → **Forum** → answers & resolves.

> **Demo note:** freshly-posted doubts aren't "overdue" yet (needs 3h). The **Remind faculty**
> and **Escalate** buttons work immediately on any unanswered doubt — use those to show the flow.

---

## Flow 5 — Tests & tasks (create → attempt → grade → chase)
**Actors:** `faculty1` (create/grade), `S105` & `S106` (attempt/submit).
**Proves:** MCQ auto-grading, task submission (incl. late flag), grading, incomplete-work chase.

**Test:**
1. **`faculty1`** → **Tests** → select `FS-DEMO` → **New test** → title, 2 questions, mark the
   correct choice each → **Create test**.
2. **`S105`** → **Tests** → the test is **open** → **Take** → answer → **Submit** → **score shown
   instantly** (auto-graded).

**Task:**
3. **`faculty1`** → **Tasks** → **New task** (choose a deadline type) → **Create**.
4. **`S106`** → **Tasks** → submit text/file for the **"Build a TODO app"** task (past deadline) →
   it's accepted but **flagged late**; submit the future task → **on time**.
5. **`faculty1`** → **Tasks** → open the task → **Grade** (score + feedback) → `S106` sees the
   grade + feedback on their Tasks page.

**Chase incomplete work:**
6. **`mis1`** → **Escalations** → **Run checks** → students who haven't attempted a test get a
   reminder (student + faculty + MIS notified).

---

## Flow 6 — Attendance & absentee follow-up (Counsellor + MIS)
**Actors:** `S101`/`S102`/`S103` (logged in earlier = present today), other students (absent),
`counselor1` and `mis1` (follow up).
**Proves:** login-based attendance, the daily roster, and Counsellor+MIS shared follow-up.

1. **`counselor1`** → **Attendance** → pick `FS-DEMO` → **Daily login attendance** (today) →
   shows **who logged in / who didn't**. The students you signed in during Flow 2 show **✓**;
   others show **✗ (absent today)**.
2. For an absentee, set the **follow-up status** dropdown → *Contacted* / *Not reachable* /
   *Resolved*.
3. **`mis1`** → **Attendance** → open the **same** batch → sees/updates the **same follow-up**
   (Counsellor + MIS share ownership).
4. Run the automated reminder from the backend terminal:
   `python manage.py send_absence_reminders` → today's absentees get a "we missed you" message.
5. **50% rule:** `mis1` → **Escalations** → **Run checks** → any student **below 50%** attendance
   triggers an alert to faculty + Counsellor + MIS.

> **Demo note:** seed attendance is ~78%, so the 50% alert may not fire for anyone. Explain the
> rule, or point at a student with few logins. The daily roster + follow-up work regardless.

---

## Flow 7 — Live classes (schedule → join → check-in → cancel)
**Actors:** `faculty1` (schedule/cancel), `S107` (join/check-in).
**Proves:** faculty-led scheduling, reminders, check-in attendance, cancellation notice.

1. **`faculty1`** → **Live classes** → **Schedule a class** for `FS-DEMO` (title, time, Meet link)
   → **Schedule + notify**. Students get email/SMS/WhatsApp/in-app (console shows them).
2. **`S107`** → **Live classes** → **Join & check-in** → opens the link; check-in is recorded.
3. **`faculty1`** → **Live classes** → **Cancel** a scheduled class → students receive a
   **cancellation** notification.

---

## Flow 8 — Video & content access closure
**Actors:** `faculty1` (upload), `S108` (watch), `mis1` (revoke/close).
**Proves:** faculty-only video upload, watermark/progress, and MIS/Admin access control.

1. **`faculty1`** → **Content** → **Upload class video** (a real MP4 shows actual playback) and a
   **note**.
2. **`S108`** → **Videos** → watch → **watermark** shows S108's identity; watching **≥80%** marks
   the video as watched.
3. **`mis1`** → **Content** → **Close course video access** (or individual revoke) → **`S108`**
   refreshes **Videos** → playback is now blocked for that course.

---

## Flow 9 — Device policy (in-class vs outside-class approval)
**Actors:** a student, `mis1` (outside class), `faculty1` (in class).
**Proves:** device binding + the time-window approval routing.

1. Sign in as **`S101`** in your **normal** window (binds the device).
2. Open an **Incognito** window (fresh device fingerprint) → sign in as **`S101`** → **blocked**
   ("new device") and a **device-change request** is created.
3. **Outside class:** **`mis1`** → **Devices** → **Approve** → now the incognito login works.
4. **In class (optional):** **`faculty1`** → schedule a live class for **now** → then
   **`faculty1`** → **Devices** → **Approve** — allowed only while that class is active.
   (Try MIS during an active class → it refuses; try Faculty with no active class → it refuses.)

---

## Flow 10 — Course completion → certification, review, next-plan
**Actors:** `admin1` (complete batch), a student, `mis1` (follow-up).
**Proves:** completion closes video access; certificate + Google review + marketing capture.

1. **`admin1`** → **Batches** → **Complete** the FS-DEMO batch (this also **closes video access**).
2. A student → **Certificate** → now shows the completed course → enter a **Certificate ID** →
   reminders stop.
3. Same student, next login → the **Google review** popup and the **next-plan** form appear
   (submit the next-plan → Admin is notified).
4. **`mis1`** → **Certificates** → sees **pending vs certified**, reminder counts, follow-up
   status, and **Send weekly reminders**.
5. **`admin1` / `mis1`** → **Engagement** → LinkedIn/Google/next-plan report.

> After this flow, re-run `python manage.py seed_demo` to set the batch **back to Active** for
> the next demo.

---

## Flow 11 — Passwords (forgot + change)
**Actors:** any account.
1. **Forgot:** logout → **Forgot password?** → enter Registration ID/email → **email OTP** →
   **phone OTP** → new password (all OTPs in the backend terminal).
2. **Change:** while signed in → **profile menu → Change password** → old + new → success toast.

## Flow 12 — Staff accounts (who can create whom)
**Actors:** `superadmin1`, `admin1`.
1. **`superadmin1`** → **Staff** → create a **Faculty** and a **MIS** account → they start
   **pending** with a setup link.
2. **`admin1`** → **Staff** → the role dropdown offers **Counsellor only** (Admin can't create
   Faculty/Admin). Create a Counsellor.

## Flow 13 — Super Admin scope + Channels + Reports
1. **`superadmin1`** → note the sidebar: **no** Activity, notes/MCQ upload, video revoke,
   batch-create or live scheduling (intentionally locked out).
2. **Channels** → send a **test message** (email/SMS/WhatsApp) → appears in the backend console.
3. **`admin1`/`mis1`** → **Reports** → pick `FS-DEMO` → download **Students / Attendance /
   Performance** CSVs.

---

## Suggested full-demo order (≈20–25 min)
1 Enrolment+setup → 2 Student experience (multi-student) → 3 Ask/answer/resolve doubt →
4 Remind/escalate doubt → 5 Tests & tasks → 6 Attendance follow-up → 7 Live classes →
8 Video access closure → 9 Device policy → 10 Completion + certification/reviews →
11 Passwords → 12 Staff accounts → 13 Super Admin/Channels/Reports.

Throughout, keep the **notification bell** in view — it fills up as each action fires, which is a
great way to show the platform is wired end-to-end.

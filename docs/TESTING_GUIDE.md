# Testing guide — every portal, every role, every flow

How to exercise the whole system by hand: accounts, passwords, and a walkthrough of what each
of the seven roles can do, in the order that makes sense to test them.

Works against a local run or the Render/Vercel test deployment
(`docs/TEMP_HOSTING_RENDER_VERCEL.md`). Differences are flagged where they matter.

---

## 1. Accounts and passwords

Everything below is created by `python manage.py seed_demo` (add `--force` outside `DEBUG`).

### Staff — one account per role

**Password for every account: `Demo!passLMS1`**

| Login ID | Role | Name | Portal URL |
|---|---|---|---|
| `superadmin1` | Super Admin | Demo Super Admin | `/super-admin` |
| `admin1` | Admin | Demo Admin | `/admin` |
| `mis1` | MIS Executive | Demo MIS | `/mis` |
| `counselor1` | Counselor | Demo Counselor | `/counselor` |
| `techsupport1` | Tech Support | Demo Tech Support | `/tech-support` |
| `faculty1` | Faculty | Anita Sharma | `/faculty` |
| `student1` | Student | Demo Student | `/student` |

### Students — enrolled in batch `FS-DEMO`

Same password. Log in at `/login/student`.

| Reg. ID | Name | Employer |
|---|---|---|
| `S101` | Asha Rao | Infosys |
| `S102` | Ravi Kumar | TCS |
| `S103` | Meena Iyer | Wipro |
| `S104` | Karthik Nair | — |
| `S105` | Sneha Patel | Accenture |
| `S106` | Arjun Menon | Infosys |
| `S107` | Divya Suresh | — |
| `S108` | Rahul Verma | Cognizant |

### Seeded data

- **Courses:** `FS` (Full Stack Development), `DS` (Data Science Foundations)
- **Batch:** `FS-DEMO`, active, Mon/Wed/Fri 18:00–20:00, faculty Anita Sharma
- Videos, two tests, two tasks, forum threads, live classes, and login attendance history

---

## 2. Two things that will confuse you if nobody says them

### Login is role-bound

You cannot log in at the wrong portal. `/login/student` with `admin1` fails with 401 even
though the password is right. Each role has its own login page — this is deliberate, not a bug.

Go to `/` and pick the portal, or navigate directly to `/login/<slug>`.

### Attendance is login-based

Attendance is **not** marked by watching a video or submitting a test. It is one row per
student per day, created when they log in. So:

- To make someone "present today", log in as them.
- Engagement events are recorded separately for history but do not move the attendance number.

---

## 3. Portal-by-portal walkthrough

Roles are ordered so each one has data to work with by the time you reach it.

---

### 3.1 Super Admin — `/super-admin`

The governance role. Deliberately **outside** day-to-day operations: no batches, no content,
no enrolment. If you are looking for those, you want Admin or MIS.

| Page | What to test |
|---|---|
| **Dashboard** | Platform-wide counts |
| **Courses** | Create a course (`code` + `name`). Only this role can |
| **Staff** | Create a staff account, change a role, suspend/reactivate |
| **Channels** | Email/SMS/WhatsApp provider config, and **Test** buttons |
| **Permissions** | Live edit of the RBAC matrix |
| **Feedback inbox** | Private student messages — no other role can read these |
| **Escalations**, **Reports**, **Attendance**, **Performance** | Read-only oversight |

**Worth testing specifically:**

**Staff → change role.** Try demoting yourself. It is refused: you cannot demote your own
Super Admin account, and you cannot demote the last active one. Without that, one click leaves
the deployment with nobody able to appoint a replacement.

**Permissions → matrix.** Toggle a role's access to an action and watch it take effect within
about a minute (there is a short cache). Two actions — `MANAGE_SETTINGS` and
`CHANGE_USER_ROLE` — are locked to Super Admin and cannot be granted away.

**Channels → Test.** On the test deployment this "succeeds" while sending nothing — the console
adapters log instead of delivering. That is expected there and fails loudly in real production.

---

### 3.2 Admin — `/admin`

Day-to-day operations.

| Page | What to test |
|---|---|
| **Batches** | Create a batch, assign faculty, move through lifecycle states |
| **Enrolment** | Bulk import students by CSV/XLSX |
| **Addresses & goodies** | Welcome-kit register |
| **Live classes** | Schedule, cancel |
| **Attendance / Performance / Reports** | Rosters, leaderboard, CSV exports |
| **Escalations** | Run the scan manually |
| **Certificates** | Certificate follow-up board |

#### The enrolment import — the flow most worth testing

`/admin/enrolment`. Required headers:

```
registration_number,name,email,phone,batch,course,faculty
```

Sample:

```csv
registration_number,name,email,phone,batch,course,faculty
S201,Priya Sharma,priya@example.com,9876500201,FS-DEMO,FS,faculty1
S202,Vikram Rao,vikram@example.com,9876500202,FS-DEMO,FS,faculty1
```

`registration_id`, `reg_no` and `reg_id` are accepted as aliases for the first column.

**Test these three things:**

1. **Validate first.** The dry run reports errors row by row without writing anything.
2. **All-or-nothing.** Put one bad row in a good file (blank email, unknown batch). The whole
   import is rejected and nothing is created. Fix the row, re-upload, all rows land together.
3. **Setup links.** Imported students are `PENDING` until they complete setup. Use the
   **Setup link** button on each row.

Search for the student after importing rather than scanning the list — it is paginated at 25
and ordered by registration number, so a new row is not necessarily on page 1.

#### Batch lifecycle

`DRAFT → ACTIVE → COMPLETED`. Try deleting a batch that has issued certificates: refused with
409, because certificates are the academic record. Deleting a draft batch works normally.

---

### 3.3 MIS Executive — `/mis`

The widest operational role — everything Admin does, plus content and devices.

| Page | What to test |
|---|---|
| **Content** | Upload videos and materials |
| **Devices** | Approve/reject device-change requests |
| **Utility links** | Public notice board |
| **Tests / Tasks** | Create and grade |
| **Engagement** | LinkedIn / Google review / next-plan reports |
| **Certificates** | Follow-up board |

**Content upload.** Try uploading a `.exe` renamed to `.mp4` — rejected. Validation checks size,
extension, declared type **and the file's actual magic bytes**, so renaming does not get past it.

**Video access control.** Revoke a student's access to a batch's videos, log in as them and
confirm playback is blocked, then restore it.

**Devices.** See §3.5 for how to generate a request to approve.

> **Note:** on the test deployment, uploaded files disappear on redeploy. Rows survive, bytes
> do not. Upload right before you demo.

---

### 3.4 Faculty — `/faculty`

Scoped to their own batches. `faculty1` teaches `FS-DEMO`.

| Page | What to test |
|---|---|
| **Batches** | Only their own — this is the scoping test |
| **My skills** | Faculty profile |
| **Content / Tests / Tasks** | Create, and grade submissions |
| **Live classes** | Schedule for their batch |
| **Forum** | Answer student doubts |
| **Attendance / Performance** | Their batch's roster |

**Scoping.** Create a second batch as Admin, assign it to a *different* faculty, then confirm
`faculty1` cannot see it. Object-level scoping is enforced server-side, not just hidden in the
UI.

**Grading round-trip.** Faculty creates a test → student takes it → faculty grades → student
sees the grade and gets a notification. MCQ tests auto-grade on submit; file and Colab tests
are graded by hand out of the test's max score.

---

### 3.5 Tech Support — `/tech-support`

Two jobs: doubts and devices.

| Page | What to test |
|---|---|
| **Forum** | All batches' doubts |
| **Doubt monitor** | Unanswered queue with overdue flags |
| **Devices** | Approve device changes outside class hours |

**Doubt monitor.** Anything waiting longer than the response window (default 3h) is flagged
**Overdue**. The status counts beside the list describe the whole dataset, not just the page.
"Remind faculty" notifies the batch's faculty.

**Device policy — the flow worth understanding.** A student is bound to the first device they
sign in from. Signing in from a different browser blocks them and raises an approval request:

- **During a live class** → their Faculty approves.
- **Outside class hours** → Tech Support approves.
- **After the course ends** → still possible, but Tech Support only.

**To generate a request:** log in as `S101` in your normal browser, then again in a private
window (different fingerprint). The second attempt is blocked and creates the request.

Two clicks on Approve is safe — the second gets a 409 rather than double-approving, and the
button is disabled while the first is in flight.

---

### 3.6 Counselor — `/counselor`

Narrow by design: student welfare.

| Page | What to test |
|---|---|
| **Attendance** | Absentee roster and follow-up status |
| **Performance** | Batch standing |
| **Reports** | CSV exports |

**Follow-up.** On the daily roster, set a status (Pending / Contacted / Not reachable /
Resolved / Escalated) and add a note. Both persist. Note that leaving the note blank does not
wipe an existing one — deliberate, so two people working the same list do not erase each
other's work.

**The 50% rule.** A student below 50% attendance is escalated. It is strictly *below* — exactly
50% is not escalated, 49.5% is.

---

### 3.7 Student — `/student`

| Page | What to test |
|---|---|
| **Dashboard** | Progress, streak, what is due |
| **Videos** | Watch; 80% marks complete |
| **Tests / Tasks** | Take and submit |
| **Live classes** | Join links |
| **Calendar** | Schedule |
| **Attendance / Performance** | Own numbers only |
| **Forum** | Ask doubts (students cannot reply) |
| **Certificate** | Enter Certificate ID after completion |
| **Message management** | Private feedback to Super Admin |

**One attempt per test.** Submit twice — the second is refused. This is enforced by a database
constraint, not just a UI check.

**Videos are view-only.** Notes render in an embedded viewer with no download control. This is
a deterrent, not DRM — the browser necessarily receives the bytes.

**Feedback.** Goes only to Super Admin, capped at 5/hour.

---

## 4. Cross-cutting flows

### 4.1 Student setup — the full onboarding chain

1. Admin/MIS imports the student (§3.2)
2. Student receives a setup link (in test environments, read it from the server log)
3. Open the link → **Step 1**: email OTP
4. **Step 2**: phone OTP
5. **Step 3**: set a password → account becomes `ACTIVE`
6. Log in at `/login/student`

In `DEBUG`, the OTP is shown on the page as a `dev code` — no email needed. In production it is
never exposed.

**Worth testing:** enter a wrong OTP repeatedly. It locks after a handful of attempts, and
resends are capped.

### 4.2 Forgot password

`/forgot-password` → identify → email OTP → phone OTP → new password.

Responses are deliberately identical whether or not the account exists, so the endpoint cannot
be used to discover who has an account.

**Worth testing:** start a reset, then change the password normally instead. The outstanding
reset link is invalidated — it cannot be used afterwards to undo the change.

### 4.3 Two-factor authentication (staff)

`/<role>/security` → enrol → scan the QR in any authenticator → confirm a code.

**Two behaviours worth knowing:**

- **A code works once.** Confirm 2FA and immediately log in and you must wait for the next
  code. This is the standard (RFC 6238) and prevents replay of a code seen over a shoulder.
- **Five wrong codes locks the device.** A Super Admin clears it via
  `POST /api/v1/auth/totp/<user-id>/reset/`. The user keeps their authenticator entry.

### 4.4 Suspension takes effect immediately

Log in as `S101` in one browser. As Admin, suspend them. Refresh the student's page — access is
gone on the very next request, not whenever the cookie expires.

### 4.5 Scheduled jobs

Not automatic in dev or on the test deployment. Run by hand:

```bash
python manage.py send_absence_reminders      # "we missed you today"
python manage.py run_escalations             # incomplete tests + 50% attendance
python manage.py send_certificate_reminders  # weekly, until Certificate ID entered
python manage.py send_due_reminders          # live class reminders
python manage.py send_engagement_reminders   # LinkedIn / review / next-plan
python manage.py purge_old_data              # retention
```

All are safe to run twice — a second run in the same window sends nothing.

---

## 5. Things that should fail (test these too)

A feature is only proven when the refusals work.

| Try this | Expected |
|---|---|
| Log in at the wrong portal | 401 |
| Student opens `/admin/batches` | Redirected — and the API refuses independently |
| Faculty opens another faculty's batch | 403 |
| Student calls the review report endpoint | 403 |
| Submit the same test twice | Refused |
| Upload `.exe` renamed to `.mp4` | Rejected on content, not extension |
| Import a file with one bad row | Whole import rejected |
| Delete a batch with certificates | 409 |
| Demote the last Super Admin | 400 |
| Approve one device request twice | Second gets 409 |
| Suspended user keeps using an open tab | Blocked on next request |

**On URL-guessing:** the frontend hides pages by role, but that is cosmetic. The server enforces
the same rules independently. If you find a URL that returns data it should not, that is a real
bug — report it.

---

## 6. When something looks wrong

| Symptom | Likely cause |
|---|---|
| Login works, next page bounces to login | Cookie not sticking — cross-origin config (see hosting doc §Route A) |
| "CSRF verification failed" | `CSRF_TRUSTED_ORIGINS` missing the frontend URL |
| Everything empty, no error | Check for a red error panel — a failed load is distinct from empty |
| Videos 404 | Test deployment: files lost on redeploy |
| No email or SMS | Expected on test deployments — read the server log |
| Nothing on first load, then fine | Free-tier cold start, ~50s |

The API is self-documenting at `/api/v1/docs/` if you want to poke at endpoints directly.

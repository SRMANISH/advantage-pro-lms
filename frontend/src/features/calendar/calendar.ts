/** Pure calendar helpers (unit-tested): Google Calendar links + month-grid layout. */

export interface CalendarEvent {
  id: string;
  title: string;
  scheduled_at: string; // ISO
  duration_minutes: number;
  location?: string;
  details?: string;
}

/** Format a Date as the UTC basic form Google Calendar expects: YYYYMMDDTHHMMSSZ. */
function toGCalUTC(d: Date): string {
  return d
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "");
}

/**
 * Build an "Add to Google Calendar" template URL for one event. This is a one-way
 * add-to-calendar link (no OAuth / two-way sync) — the pragmatic, credential-free
 * integration; the class is also pushed as an immediate in-app/email/SMS/WhatsApp
 * notification the moment faculty schedule it.
 */
export function googleCalendarUrl(event: CalendarEvent): string {
  const start = new Date(event.scheduled_at);
  const end = new Date(start.getTime() + event.duration_minutes * 60_000);
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: event.title,
    dates: `${toGCalUTC(start)}/${toGCalUTC(end)}`,
    details: event.details ?? "",
    location: event.location ?? "",
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

export interface MonthCell {
  date: Date;
  inMonth: boolean;
}

/** A 6-row (42-cell) month grid starting on Monday, covering the month of `anchor`. */
export function monthGrid(anchor: Date): MonthCell[] {
  const year = anchor.getFullYear();
  const month = anchor.getMonth();
  const first = new Date(year, month, 1);
  // Monday-start offset: JS getDay() is 0=Sun..6=Sat.
  const offset = (first.getDay() + 6) % 7;
  const gridStart = new Date(year, month, 1 - offset);
  return Array.from({ length: 42 }, (_, i) => {
    const date = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
    return { date, inMonth: date.getMonth() === month };
  });
}

/** Group events by local YYYY-MM-DD for quick day-cell lookups. */
export function eventsByDay(events: CalendarEvent[]): Record<string, CalendarEvent[]> {
  const map: Record<string, CalendarEvent[]> = {};
  for (const e of events) {
    const d = new Date(e.scheduled_at);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
      d.getDate(),
    ).padStart(2, "0")}`;
    (map[key] ??= []).push(e);
  }
  return map;
}

export function dayKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}

/** A batch's recurring weekly class slot (from batch.class_days + times). */
export interface WeeklySchedule {
  batch_code: string;
  class_days: string[]; // e.g. ["mon","wed","fri"]
  start_time: string | null; // "18:00"
  end_time: string | null;
  start_date: string; // "YYYY-MM-DD"
  end_date: string;
}

// JS Date.getDay(): 0=Sun..6=Sat.
const DAY_INDEX: Record<string, number> = {
  sun: 0,
  mon: 1,
  tue: 2,
  wed: 3,
  thu: 4,
  fri: 5,
  sat: 6,
};

function minutesBetween(start: string | null, end: string | null): number {
  if (!start || !end) return 120;
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  const mins = eh * 60 + em - (sh * 60 + sm);
  return mins > 0 ? mins : 120;
}

/**
 * Project each batch's recurring weekly class onto the visible month cells: one event per
 * matching weekday that falls inside the batch's [start_date, end_date] window. This makes
 * a student's regular timetable appear on the calendar, not just ad-hoc live classes.
 */
export function weeklyScheduleEvents(
  schedules: WeeklySchedule[],
  cells: MonthCell[],
): CalendarEvent[] {
  const events: CalendarEvent[] = [];
  for (const s of schedules) {
    const days = new Set(s.class_days.map((d) => DAY_INDEX[d.toLowerCase()]));
    const [hh, mm] = (s.start_time ?? "00:00").split(":").map(Number);
    const startDay = new Date(`${s.start_date}T00:00:00`);
    const endDay = new Date(`${s.end_date}T23:59:59`);
    const duration = minutesBetween(s.start_time, s.end_time);
    for (const cell of cells) {
      const d = cell.date;
      if (!days.has(d.getDay())) continue;
      if (d < startDay || d > endDay) continue;
      const scheduled = new Date(d.getFullYear(), d.getMonth(), d.getDate(), hh || 0, mm || 0);
      events.push({
        id: `sched-${s.batch_code}-${dayKey(d)}`,
        title: `${s.batch_code} class`,
        scheduled_at: scheduled.toISOString(),
        duration_minutes: duration,
        details: `Regular ${s.batch_code} class.`,
      });
    }
  }
  return events;
}

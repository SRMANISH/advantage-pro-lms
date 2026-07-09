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
  return d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
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

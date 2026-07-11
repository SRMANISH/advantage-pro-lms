import {
  dayKey,
  eventsByDay,
  googleCalendarUrl,
  monthGrid,
  weeklyScheduleEvents,
  type CalendarEvent,
} from "./calendar";

const event = (over: Partial<CalendarEvent> = {}): CalendarEvent => ({
  id: "1",
  title: "React basics",
  scheduled_at: "2026-03-10T12:30:00.000Z",
  duration_minutes: 120,
  location: "https://meet.example/x",
  details: "FS-DEMO",
  ...over,
});

describe("googleCalendarUrl", () => {
  it("builds a TEMPLATE render URL with UTC start/end derived from the duration", () => {
    const url = new URL(googleCalendarUrl(event()));
    expect(url.origin + url.pathname).toBe("https://calendar.google.com/calendar/render");
    expect(url.searchParams.get("action")).toBe("TEMPLATE");
    expect(url.searchParams.get("text")).toBe("React basics");
    // 12:30 + 120min = 14:30 UTC.
    expect(url.searchParams.get("dates")).toBe("20260310T123000Z/20260310T143000Z");
    expect(url.searchParams.get("location")).toBe("https://meet.example/x");
  });
});

describe("monthGrid", () => {
  it("returns 42 cells starting on the Monday of the first week", () => {
    const grid = monthGrid(new Date(2026, 2, 15)); // March 2026 (1st is a Sunday)
    expect(grid).toHaveLength(42);
    // Monday-start grid: the first cell is Mon 2026-02-23.
    expect(dayKey(grid[0].date)).toBe("2026-02-23");
    expect(grid[0].inMonth).toBe(false);
    const firstOfMonth = grid.find((c) => dayKey(c.date) === "2026-03-01");
    expect(firstOfMonth?.inMonth).toBe(true);
  });
});

describe("weeklyScheduleEvents", () => {
  it("projects a Mon/Wed/Fri batch onto every matching in-window day of the month", () => {
    const grid = monthGrid(new Date(2026, 2, 15)); // March 2026
    const events = weeklyScheduleEvents(
      [
        {
          batch_code: "FS-1",
          class_days: ["mon", "wed", "fri"],
          start_time: "18:00",
          end_time: "20:00",
          start_date: "2026-03-01",
          end_date: "2026-03-31",
        },
      ],
      grid,
    );
    // March 2026 has 4 Mondays + 4 Wednesdays + 4 Fridays = well over one; each within window.
    expect(events.length).toBeGreaterThan(0);
    expect(events.every((e) => e.title === "FS-1 class")).toBe(true);
    // Every generated event lands on a Mon/Wed/Fri.
    expect(events.every((e) => [1, 3, 5].includes(new Date(e.scheduled_at).getDay()))).toBe(true);
    // 18:00–20:00 = 120 minutes.
    expect(events[0].duration_minutes).toBe(120);
  });

  it("excludes days outside the batch's start/end window", () => {
    const grid = monthGrid(new Date(2026, 2, 15));
    const events = weeklyScheduleEvents(
      [
        {
          batch_code: "X",
          class_days: ["mon", "tue", "wed", "thu", "fri"],
          start_time: "10:00",
          end_time: "11:00",
          start_date: "2026-03-20",
          end_date: "2026-03-25",
        },
      ],
      grid,
    );
    for (const e of events) {
      const key = dayKey(new Date(e.scheduled_at));
      expect(key >= "2026-03-20" && key <= "2026-03-25").toBe(true);
    }
  });
});

describe("eventsByDay", () => {
  it("groups events under their local day key", () => {
    // a and b share a timestamp (always the same day in any tz); c is a week later
    // (never merges regardless of the runner's timezone).
    const map = eventsByDay([
      event({ id: "a" }),
      event({ id: "b" }),
      event({ id: "c", scheduled_at: "2026-03-18T09:00:00.000Z" }),
    ]);
    const paired = Object.values(map).find((v) => v.length === 2);
    expect(paired?.map((e) => e.id).sort()).toEqual(["a", "b"]);
    expect(Object.keys(map)).toHaveLength(2);
    expect(Object.values(map).flat()).toHaveLength(3);
  });
});

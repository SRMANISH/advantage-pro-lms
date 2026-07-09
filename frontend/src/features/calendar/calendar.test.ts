import { dayKey, eventsByDay, googleCalendarUrl, monthGrid, type CalendarEvent } from "./calendar";

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

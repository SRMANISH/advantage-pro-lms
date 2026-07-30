import { useQuery } from "@tanstack/react-query";
import { CalendarPlus, ChevronLeft, ChevronRight, Video } from "lucide-react";
import { useMemo, useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Card, EmptyState, ListSkeleton, SectionHeading, cn } from "../../design-system";
import { liveApi, type LiveClass } from "../liveclasses/api";
import { PortalLayout } from "../portal/PortalLayout";
import {
  dayKey,
  eventsByDay,
  googleCalendarUrl,
  monthGrid,
  weeklyScheduleEvents,
  type CalendarEvent,
} from "./calendar";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function toEvent(lc: LiveClass): CalendarEvent {
  return {
    id: lc.id,
    title: lc.title,
    scheduled_at: lc.scheduled_at,
    duration_minutes: lc.duration_minutes ?? 120,
    location: lc.meeting_link,
    details: `${lc.batch_code} live class (${lc.platform}).`,
  };
}

export function CalendarPage({ role }: { role: RoleDef }) {
  const classes = useQuery({ queryKey: ["liveclasses"], queryFn: () => liveApi.list() });
  const schedule = useQuery({
    queryKey: ["weekly-schedule"],
    queryFn: () => liveApi.weeklySchedule(),
  });
  const [anchor, setAnchor] = useState(new Date());

  const active = (classes.data ?? []).filter((c) => c.status !== "cancelled");
  const events = active.map(toEvent);
  const grid = useMemo(() => monthGrid(anchor), [anchor]);
  // Ad-hoc live classes + the batch's recurring weekly class slots for the visible month.
  const recurring = useMemo(
    () => weeklyScheduleEvents(schedule.data ?? [], grid),
    [schedule.data, grid],
  );
  const byDay = useMemo(() => eventsByDay([...events, ...recurring]), [events, recurring]);
  const todayKey = dayKey(new Date());

  const upcoming = active
    .filter((c) => new Date(c.scheduled_at).getTime() >= Date.now())
    .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at))
    .slice(0, 8);

  const monthLabel = anchor.toLocaleString([], { month: "long", year: "numeric" });
  const step = (delta: number) =>
    setAnchor((a) => new Date(a.getFullYear(), a.getMonth() + delta, 1));

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Class calendar"
        subtitle="Your weekly classes and every scheduled live session — one tap to add to Google Calendar."
      />

      {classes.isLoading ? (
        <ListSkeleton items={4} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <button
                aria-label="Previous month"
                onClick={() => step(-1)}
                className="rounded-lg p-1.5 text-muted hover:bg-sky"
              >
                <ChevronLeft size={18} />
              </button>
              <h2 className="text-base font-medium text-ink">{monthLabel}</h2>
              <button
                aria-label="Next month"
                onClick={() => step(1)}
                className="rounded-lg p-1.5 text-muted hover:bg-sky"
              >
                <ChevronRight size={18} />
              </button>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-medium text-muted">
              {DOW.map((d) => (
                <div key={d} className="py-1">
                  {d}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {grid.map((cell) => {
                const key = dayKey(cell.date);
                const dayEvents = byDay[key] ?? [];
                return (
                  <div
                    key={key}
                    className={cn(
                      "min-h-14 rounded-lg border p-1 text-left text-xs",
                      cell.inMonth
                        ? "border-brdr bg-surface"
                        : "border-transparent bg-appbg/40 text-muted",
                      key === todayKey && "ring-1 ring-brand",
                    )}
                  >
                    <div
                      className={cn(
                        "mb-0.5",
                        key === todayKey && "font-semibold text-brand-strong",
                      )}
                    >
                      {cell.date.getDate()}
                    </div>
                    {dayEvents.slice(0, 2).map((e) => (
                      <div
                        key={e.id}
                        title={e.title}
                        className="mb-0.5 truncate rounded bg-brand/10 px-1 py-0.5 text-[10px] text-brand-strong"
                      >
                        {new Date(e.scheduled_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}{" "}
                        {e.title}
                      </div>
                    ))}
                    {dayEvents.length > 2 && (
                      <div className="text-[10px] text-muted">+{dayEvents.length - 2} more</div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">Up next</h2>
            {upcoming.length === 0 ? (
              <EmptyState title="No upcoming classes" />
            ) : (
              <div className="flex flex-col divide-y divide-brdr">
                {upcoming.map((c) => (
                  <div key={c.id} className="py-3">
                    <div className="text-sm font-medium text-ink">{c.title}</div>
                    <div className="mb-2 text-xs text-muted">
                      {new Date(c.scheduled_at).toLocaleString([], {
                        weekday: "short",
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}{" "}
                      · <Badge>{c.batch_code}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <a
                        href={googleCalendarUrl(toEvent(c))}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-lg bg-sky px-2.5 py-1 text-xs font-medium text-brand-strong hover:underline"
                      >
                        <CalendarPlus size={13} /> Add to Google Calendar
                      </a>
                      {c.meeting_link && (
                        <a
                          href={c.meeting_link}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg border border-brdr px-2.5 py-1 text-xs font-medium text-ink hover:bg-sky"
                        >
                          <Video size={13} /> Join
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </PortalLayout>
  );
}

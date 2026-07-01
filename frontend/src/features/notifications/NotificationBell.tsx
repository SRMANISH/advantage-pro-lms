import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Bell } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { cn } from "../../design-system";
import { notificationsApi } from "./api";

export function NotificationBell() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const list = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
    refetchInterval: 20000,
  });
  const items = list.data ?? [];
  const unread = items.filter((n) => !n.read).length;

  const invalidate = () => qc.invalidateQueries({ queryKey: ["notifications"] });
  const markRead = useMutation({ mutationFn: notificationsApi.markRead, onSuccess: invalidate });
  const markAll = useMutation({ mutationFn: notificationsApi.markAll, onSuccess: invalidate });

  const onItem = (id: string, link: string) => {
    markRead.mutate(id);
    setOpen(false);
    if (link) navigate(link);
  };

  return (
    <div className="relative">
      <button
        aria-label="Notifications"
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-xl p-2 text-muted transition-colors hover:bg-sky hover:text-navy"
      >
        <Bell size={20} />
        {unread > 0 && (
          <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white ring-2 ring-surface">
            {unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 z-20 mt-2 w-80 overflow-hidden rounded-2xl border border-brdr bg-surface shadow-lift"
            >
              <div className="flex items-center justify-between border-b border-brdr bg-sky/40 px-4 py-3">
                <span className="text-sm font-semibold text-ink">
                  Notifications{unread > 0 && <span className="ml-1 text-muted">· {unread} new</span>}
                </span>
                {unread > 0 && (
                  <button
                    onClick={() => markAll.mutate()}
                    className="text-xs font-medium text-brand-strong hover:underline"
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-96 overflow-auto">
                {items.length === 0 ? (
                  <div className="px-4 py-10 text-center text-sm text-muted">
                    You&apos;re all caught up.
                  </div>
                ) : (
                  items.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => onItem(n.id, n.link)}
                      className={cn(
                        "block w-full border-b border-brdr px-4 py-3 text-left text-sm transition-colors hover:bg-sky/50",
                        n.read ? "" : "bg-brand/[0.05]",
                      )}
                    >
                      <span className="flex items-start gap-2.5">
                        <span
                          className={cn(
                            "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                            n.read ? "ring-1 ring-brdr" : "bg-brand",
                          )}
                        />
                        <span className={n.read ? "text-muted" : "text-ink"}>{n.message}</span>
                      </span>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

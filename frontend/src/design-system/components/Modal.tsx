import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, type ReactNode } from "react";

import { cn } from "../utils/cn";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  maxWidth?: string;
}

/** Elements that can hold focus, in document order, excluding anything disabled or removed
 *  from the tab sequence. */
const FOCUSABLE =
  "a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), " +
  'select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  maxWidth = "max-w-md",
}: ModalProps) {
  const panel = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  // The dialog already claimed role="dialog" and aria-modal="true", which is a promise to
  // assistive tech that focus is managed and the rest of the page is inert. None of it was
  // implemented: Tab walked straight out of the dialog into the page behind it, Escape did
  // nothing, and closing dropped focus onto <body> so a keyboard user lost their place
  // entirely. Announcing that contract and not keeping it is worse than never announcing it.
  useEffect(() => {
    if (!open) return;

    openerRef.current = document.activeElement as HTMLElement | null;

    // Focus the first control, or the panel itself if the dialog is purely informational.
    const focusFirst = () => {
      const target = panel.current?.querySelector<HTMLElement>(FOCUSABLE) ?? panel.current;
      target?.focus();
    };
    // After the entry animation commits, so the node exists and is visible.
    const raf = requestAnimationFrame(focusFirst);

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel.current) return;

      // Visibility filtered by attribute, not by offsetParent. offsetParent is a layout
      // property: it is null under any environment without a layout engine, which would make
      // this list empty and turn the trap into "Tab does nothing" — a worse failure than
      // occasionally including a hidden control, and one that no unit test could observe.
      const items = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => !el.hasAttribute("hidden") && el.closest("[hidden],[aria-hidden='true']") === null,
      );
      if (items.length === 0) {
        e.preventDefault(); // nothing to move to — keep focus inside
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;

      // Wrap at both ends, and pull focus back in if it has escaped the panel entirely.
      if (e.shiftKey && (active === first || !panel.current.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !panel.current.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("keydown", onKeyDown, true);
      // Put focus back on whatever opened the dialog, rather than leaving the keyboard user
      // at the top of the document with no idea where they are.
      openerRef.current?.focus?.();
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div
            className="absolute inset-0 bg-navyDeep/40 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300, damping: 26 }}
            className={cn(
              "relative w-full rounded-2xl border border-brdr bg-surface p-5 shadow-lift",
              maxWidth,
            )}
          >
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-1 text-sm text-muted">{description}</p>}
            <div className={title || description ? "mt-4" : ""}>{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

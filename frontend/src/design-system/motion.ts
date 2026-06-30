import type { Transition, Variants } from "framer-motion";

// Shared easing — a soft "ease-out expo" that feels premium without being slow.
export const easeOut: Transition = { duration: 0.4, ease: [0.22, 1, 0.36, 1] };

export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.3 } },
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: easeOut },
};

/** Parent that staggers its children in. Pair with `staggerItem` on each child. */
export const staggerContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.03 } },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: easeOut },
};

/** Route-level page transition. */
export const pageVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: easeOut },
  exit: { opacity: 0, y: -6, transition: { duration: 0.2 } },
};

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { pageVariants } from "../motion";

/** Wrap a route's content for a consistent enter/exit transition. */
export function PageTransition({ children }: { children: ReactNode }) {
  return (
    <motion.div variants={pageVariants} initial="hidden" animate="show" exit="exit">
      {children}
    </motion.div>
  );
}

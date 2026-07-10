import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, ExternalLink, Pin, Youtube } from "lucide-react";
import { Link } from "react-router-dom";

import { Logo, Skeleton, cn, staggerContainer, staggerItem } from "../design-system";
import { utilityApi, youtubeThumb } from "../features/utility/api";

/** Public notice board — a full-page corkboard of links curated by the MIS desk. */
export function UtilityLinksBoardPage() {
  const links = useQuery({ queryKey: ["utility-links-public"], queryFn: utilityApi.list });
  const items = links.data ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky via-appbg to-surface">
      <header className="sticky top-0 z-40 border-b border-brdr/70 bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface shadow-card ring-1 ring-black/5">
              <Logo size={38} />
            </span>
            <div className="leading-tight">
              <div className="text-[15px] font-semibold text-ink">Advantage Pro</div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted">
                Learning Management
              </div>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-brand-strong"
            >
              <ArrowLeft size={15} /> Home
            </Link>
            <Link
              to="/#signin"
              className="rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-strong"
            >
              Sign in
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brdr bg-surface px-3 py-1 text-xs font-medium tracking-wide text-navy shadow-card">
            <Pin size={12} className="text-logoRed" /> THE NOTICE BOARD
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Utility links
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Hand-picked sessions, playlists and resources — pinned fresh by the MIS desk.
            Tap any note to open it.
          </p>
        </motion.div>

        <div className="relative mt-8 rounded-3xl border border-brand/20 bg-gradient-to-br from-sky/70 via-surface to-surface p-6 shadow-card sm:p-10">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-3xl opacity-[0.12]"
            style={{
              backgroundImage: "radial-gradient(#00A0E0 1px, transparent 1px)",
              backgroundSize: "18px 18px",
            }}
          />
          {links.isLoading ? (
            <div className="relative grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-52 rounded-xl bg-white/70" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <p className="relative py-14 text-center text-sm text-muted">
              The board is empty for now — check back soon.
            </p>
          ) : (
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="show"
              className="relative grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
            >
              {items.map((l, i) => {
                const ytThumb = youtubeThumb(l.url);
                const thumb = l.thumbnail_url ?? ytThumb;
                return (
                  <motion.a
                    key={l.id}
                    variants={staggerItem}
                    href={l.url}
                    target="_blank"
                    rel="noreferrer"
                    whileHover={{ rotate: 0, y: -4, scale: 1.02 }}
                    className={cn(
                      "group relative block rounded-xl bg-surface p-3 shadow-lift transition-shadow",
                      i % 3 === 0
                        ? "rotate-[-1.2deg]"
                        : i % 3 === 1
                          ? "rotate-[0.8deg]"
                          : "rotate-[-0.5deg]",
                    )}
                  >
                    <span className="absolute -top-2 left-1/2 z-10 h-4 w-4 -translate-x-1/2 rounded-full bg-logoRed shadow-[0_2px_4px_rgba(0,0,0,0.35)] ring-2 ring-white/60" />
                    {l.pinned && (
                      <span className="absolute right-2 top-2 z-10 rounded-full bg-logoYellow px-2 py-0.5 text-[10px] font-semibold text-ink shadow-sm">
                        PINNED
                      </span>
                    )}
                    {thumb ? (
                      <img src={thumb} alt="" className="h-40 w-full rounded-lg object-cover" />
                    ) : (
                      <div className="flex h-40 w-full items-center justify-center rounded-lg bg-sky">
                        <ExternalLink className="text-brand-strong" />
                      </div>
                    )}
                    <div className="flex items-start gap-2 px-1 pb-1 pt-3">
                      {ytThumb && !l.thumbnail_url && (
                        <Youtube size={16} className="mt-0.5 shrink-0 text-danger" />
                      )}
                      <span className="text-sm font-semibold leading-snug text-ink group-hover:text-brand-strong">
                        {l.title}
                      </span>
                    </div>
                  </motion.a>
                );
              })}
            </motion.div>
          )}
        </div>
      </main>

      <footer className="border-t border-brdr bg-surface/60 py-6 text-center text-xs text-muted">
        Advantage Pro · Vectra Technosoft · since 1998
      </footer>
    </div>
  );
}

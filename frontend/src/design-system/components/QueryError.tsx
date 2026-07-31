import { AlertTriangle } from "lucide-react";

import { Button } from "./Button";

/**
 * What a page shows when a GET fails.
 *
 * Every feature page used to branch on loading and loaded only, so a failed request fell
 * through to the empty state: the server being down looked exactly like having no doubts, no
 * students, no batches. That is worse than an error, because the user believes it — they act
 * on "there is nothing here" rather than retrying or reporting it.
 *
 * Mutations already surface their own failures through the global error toast (lib/api.ts);
 * this is only for reads, which have no such path.
 */
export function QueryError({
  title = "Could not load this",
  hint = "Something went wrong fetching this data. Check your connection and try again.",
  onRetry,
}: {
  title?: string;
  hint?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-2xl border border-brdr bg-surface px-6 py-10 text-center"
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-danger/10 text-danger">
        <AlertTriangle size={20} aria-hidden="true" />
      </span>
      <div>
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted">{hint}</p>
      </div>
      {onRetry && (
        <Button variant="soft" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

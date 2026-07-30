import { cn } from "../utils/cn";

/** The shape every batch list shares (`batchesApi.listBatches` and `attendanceApi.reviewBatches`). */
export interface BatchOption {
  id: string;
  code: string;
  name: string;
}

/**
 * The batch picker used across the ops pages. Presentational on purpose — it takes the
 * options rather than fetching, because callers draw from two different endpoints
 * (all batches vs. the batches a user may review) and the choice is a permission concern,
 * not a display one.
 *
 * `placeholder` doubles as the empty-value option: pass `includeAll` semantics by wording it
 * "All batches" where an empty selection means unfiltered, or leave the default where a
 * batch must be chosen before the page shows anything.
 */
export function BatchSelect({
  id,
  value,
  onChange,
  batches,
  label = "Batch",
  placeholder = "Select a batch…",
  hideLabel = false,
  className,
}: {
  id: string;
  value: string;
  onChange: (batchId: string) => void;
  batches: BatchOption[] | undefined;
  label?: string;
  placeholder?: string;
  hideLabel?: boolean;
  className?: string;
}) {
  return (
    <>
      {hideLabel ? (
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
      ) : (
        <label htmlFor={id} className="mb-1 block text-sm text-muted">
          {label}
        </label>
      )}
      <select
        id={id}
        className={cn(
          "h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm",
          className,
        )}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {batches?.map((b) => (
          <option key={b.id} value={b.id}>
            {b.code} — {b.name}
          </option>
        ))}
      </select>
    </>
  );
}

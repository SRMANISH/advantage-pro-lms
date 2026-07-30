import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";

interface Prompt {
  message: string;
  courses: { code: string; name: string }[];
}

export function UpsellPrompt() {
  const q = useQuery({
    queryKey: ["upsell"],
    queryFn: async () => (await api.get<{ prompt: Prompt | null }>("/upsell/")).data.prompt,
  });

  if (!q.data) return null;

  return (
    <div className="rounded-2xl border border-brdr bg-surface p-4">
      <span className="text-xs font-medium" style={{ color: "rgb(var(--color-violet))" }}>
        Recommended next step
      </span>
      <p className="mt-1 text-sm text-ink">{q.data.message}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {q.data.courses.map((c) => (
          <span key={c.code} className="rounded-full bg-sky px-3 py-1 text-xs text-navy">
            {c.name}
          </span>
        ))}
      </div>
    </div>
  );
}

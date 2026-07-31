import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Youtube } from "lucide-react";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ListSkeleton,
  QueryError,
  SectionHeading,
  useToast,
} from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { utilityApi, youtubeThumb } from "./api";

/** MIS curates the public notice board shown on the landing page. */
export function UtilityLinksPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const links = useQuery({ queryKey: ["utility-links"], queryFn: utilityApi.list });

  const [form, setForm] = useState({ title: "", url: "", pinned: false });
  const [thumbnail, setThumbnail] = useState<File | null>(null);
  const invalidate = () => qc.invalidateQueries({ queryKey: ["utility-links"] });

  const create = useMutation({
    mutationFn: () => utilityApi.create({ ...form, thumbnail }),
    onSuccess: () => {
      setForm({ title: "", url: "", pinned: false });
      setThumbnail(null);
      invalidate();
      toast.show("Link pinned to the notice board.", "success");
    },
    onError: () => toast.show("Could not add the link — check the URL and image.", "error"),
  });
  const remove = useMutation({
    mutationFn: (id: string) => utilityApi.remove(id),
    onSuccess: () => {
      invalidate();
      toast.show("Link removed.", "success");
    },
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Utility links"
        subtitle="Curate the public notice board on the landing page — YouTube sessions, resources and announcements."
      />

      <Card className="mb-6">
        <h2 className="mb-3 text-base font-medium text-ink">Pin a new link</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            placeholder="Heading (e.g. 'React basics — full session')"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <Input
            placeholder="Link (YouTube or any URL)"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={form.pinned}
              onChange={(e) => setForm({ ...form, pinned: e.target.checked })}
            />
            Pin to the top of the board
          </label>
          <div>
            <label htmlFor="util-thumb" className="mb-1 block text-xs font-medium text-muted">
              Thumbnail image (optional — else a YouTube preview is used)
            </label>
            <input
              id="util-thumb"
              type="file"
              accept="image/png,image/jpeg,image/gif"
              onChange={(e) => setThumbnail(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-sky file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-brand-strong"
            />
            {thumbnail && <p className="mt-1 text-xs text-muted">{thumbnail.name}</p>}
          </div>
          <div className="sm:col-span-2 sm:text-right">
            <Button
              onClick={() => create.mutate()}
              disabled={!form.title || !form.url || create.isPending}
            >
              {create.isPending ? "Adding…" : "Add to notice board"}
            </Button>
          </div>
        </div>
      </Card>

      <SectionHeading title="On the board" />
      {links.isLoading ? (
        <ListSkeleton items={3} />
      ) : links.isError ? (
        <QueryError onRetry={() => links.refetch()} />
      ) : links.data && links.data.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {links.data.map((l) => {
            const ytThumb = youtubeThumb(l.url);
            const thumb = l.thumbnail_url ?? ytThumb;
            return (
              <Card key={l.id} className="overflow-hidden p-0">
                {thumb ? (
                  <img src={thumb} alt="" className="h-36 w-full object-cover" />
                ) : (
                  <div className="flex h-36 w-full items-center justify-center bg-sky">
                    <ExternalLink className="text-brand-strong" />
                  </div>
                )}
                <div className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {ytThumb && !l.thumbnail_url && (
                        <Youtube size={15} className="shrink-0 text-danger" />
                      )}
                      <span className="text-sm font-semibold text-ink">{l.title}</span>
                    </div>
                    {l.pinned && <Badge tone="warning">Pinned</Badge>}
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <a
                      href={l.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-medium text-brand-strong hover:underline"
                    >
                      Open link ↗
                    </a>
                    <button
                      onClick={() => remove.mutate(l.id)}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-danger hover:bg-danger/10"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="Nothing on the board yet"
          hint="Pin your first YouTube session or resource above."
        />
      )}
    </PortalLayout>
  );
}

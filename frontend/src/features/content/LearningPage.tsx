import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ListSkeleton,
  SectionHeading,
  QueryError,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { UpsellPrompt } from "../upsell/UpsellPrompt";
import { contentApi, type MaterialItem, type VideoItem } from "./api";
import { MaterialViewer } from "./MaterialViewer";
import { VideoPlayer } from "./VideoPlayer";

export function LearningPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const videos = useQuery({ queryKey: ["videos"], queryFn: () => contentApi.listVideos() });
  const materials = useQuery({
    queryKey: ["materials"],
    queryFn: () => contentApi.listMaterials(),
  });
  const [active, setActive] = useState<VideoItem | null>(null);
  const [activeNote, setActiveNote] = useState<MaterialItem | null>(null);
  const watermark = `${user?.full_name || user?.username} · ${user?.username}`;

  return (
    <PortalLayout role={role}>
      {!active && !activeNote && (
        <SectionHeading
          title="Videos"
          subtitle="Your class recordings and notes — streamed in-app, no downloads."
        />
      )}

      {active ? (
        <div className="grid gap-3">
          <Button variant="ghost" className="w-fit" onClick={() => setActive(null)}>
            ← Back to list
          </Button>
          <h2 className="text-base font-medium text-ink">{active.title}</h2>
          <VideoPlayer video={active} watermark={watermark} />
          <p className="text-xs text-muted">
            Watching ≥80% marks you present. Playback is in-app only — no downloads.
          </p>
          <UpsellPrompt />
        </div>
      ) : activeNote ? (
        <div className="grid gap-3">
          <Button variant="ghost" className="w-fit" onClick={() => setActiveNote(null)}>
            ← Back to list
          </Button>
          <h2 className="text-base font-medium text-ink">{activeNote.title}</h2>
          <MaterialViewer material={activeNote} watermark={watermark} />
        </div>
      ) : (
        <div className="grid gap-4">
          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">Class videos</h2>
            {videos.isLoading ? (
              <ListSkeleton items={3} />
            ) : videos.isError ? (
              <QueryError onRetry={() => videos.refetch()} />
            ) : videos.data && videos.data.length > 0 ? (
              <div className="flex flex-col divide-y divide-brdr">
                {videos.data.map((v) => (
                  <div key={v.id} className="flex items-center justify-between py-2">
                    <div className="text-sm">
                      <span className="font-medium text-ink">{v.title}</span>
                      {v.progress?.completed && (
                        <Badge tone="success" className="ml-2">
                          watched
                        </Badge>
                      )}
                    </div>
                    <Button onClick={() => setActive(v)}>Watch</Button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No videos yet" hint="Class recordings will appear here." />
            )}
          </Card>

          <Card>
            <h2 className="mb-1 text-base font-medium text-ink">Notes &amp; materials</h2>
            <p className="mb-3 text-xs text-muted">
              Open to read in the app — view-only, no downloads.
            </p>
            {materials.data && materials.data.length > 0 ? (
              <div className="flex flex-col divide-y divide-brdr">
                {materials.data.map((m) => (
                  <div key={m.id} className="flex items-center justify-between py-2">
                    <span className="text-sm font-medium text-ink">{m.title}</span>
                    <Button variant="ghost" onClick={() => setActiveNote(m)}>
                      View
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No notes yet" />
            )}
          </Card>
        </div>
      )}
    </PortalLayout>
  );
}

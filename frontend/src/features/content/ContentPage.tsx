import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Button, Card, Input, Select } from "../../design-system";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";
import { contentApi } from "./api";

export function ContentPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const [batchId, setBatchId] = useState("");
  const videos = useQuery({
    queryKey: ["videos", batchId],
    queryFn: () => contentApi.listVideos(batchId || undefined),
  });
  const materials = useQuery({
    queryKey: ["materials", batchId],
    queryFn: () => contentApi.listMaterials(batchId || undefined),
  });

  const [vTitle, setVTitle] = useState("");
  const [vFile, setVFile] = useState<File | null>(null);
  const vRef = useRef<HTMLInputElement>(null);
  const [mTitle, setMTitle] = useState("");
  const [mFile, setMFile] = useState<File | null>(null);
  const mRef = useRef<HTMLInputElement>(null);

  const uploadVideo = useMutation({
    mutationFn: () => contentApi.uploadVideo(batchId, vTitle, vFile!),
    onSuccess: () => {
      setVTitle("");
      setVFile(null);
      if (vRef.current) vRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["videos"] });
    },
  });
  const uploadMaterial = useMutation({
    mutationFn: () => contentApi.uploadMaterial(batchId, mTitle, mFile!),
    onSuccess: () => {
      setMTitle("");
      setMFile(null);
      if (mRef.current) mRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["materials"] });
    },
  });

  return (
    <PortalLayout role={role}>
      <h1 className="mb-4 text-xl font-medium text-ink">Content</h1>

      <Card className="mb-6">
        <label className="mb-1 block text-sm text-muted">Batch</label>
        <Select value={batchId} onChange={(e) => setBatchId(e.target.value)}>
          <option value="">All my batches</option>
          {batches.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.code} — {b.name}
            </option>
          ))}
        </Select>
        {!batchId && (
          <p className="mt-2 text-xs text-muted">Select a batch to upload videos or notes.</p>
        )}
      </Card>

      {batchId && (
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">Upload class video</h2>
            <div className="flex flex-col gap-2">
              <Input placeholder="Title" value={vTitle} onChange={(e) => setVTitle(e.target.value)} />
              <input
                ref={vRef}
                type="file"
                accept="video/*"
                onChange={(e) => setVFile(e.target.files?.[0] ?? null)}
                className="text-sm"
              />
              <Button
                onClick={() => uploadVideo.mutate()}
                disabled={!vTitle || !vFile || uploadVideo.isPending}
              >
                {uploadVideo.isPending ? "Uploading…" : "Upload video"}
              </Button>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">Upload note / material</h2>
            <div className="flex flex-col gap-2">
              <Input placeholder="Title" value={mTitle} onChange={(e) => setMTitle(e.target.value)} />
              <input
                ref={mRef}
                type="file"
                onChange={(e) => setMFile(e.target.files?.[0] ?? null)}
                className="text-sm"
              />
              <Button
                variant="soft"
                onClick={() => uploadMaterial.mutate()}
                disabled={!mTitle || !mFile || uploadMaterial.isPending}
              >
                {uploadMaterial.isPending ? "Uploading…" : "Upload note"}
              </Button>
            </div>
          </Card>
        </div>
      )}

      <Card className="mb-6">
        <h2 className="mb-3 text-base font-medium text-ink">Videos</h2>
        {videos.data && videos.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {videos.data.map((v) => (
              <div key={v.id} className="py-2 text-sm">
                <span className="font-medium text-ink">{v.title}</span>
                {v.uploaded_by_name && (
                  <span className="text-muted"> · {v.uploaded_by_name}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No videos yet.</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Notes &amp; materials</h2>
        {materials.data && materials.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {materials.data.map((m) => (
              <div key={m.id} className="py-2 text-sm font-medium text-ink">
                {m.title}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No notes yet.</p>
        )}
      </Card>
    </PortalLayout>
  );
}

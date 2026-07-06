import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Button,
  Card,
  EmptyState,
  FileUpload,
  Input,
  SectionHeading,
  Select,
  useToast,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";
import { contentApi } from "./api";

export function ContentPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const canUploadVideo = user?.role === "faculty"; // videos = Faculty only
  const isMis = user?.role === "mis"; // MIS revokes/closes video access
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const [batchId, setBatchId] = useState("");
  const [closed, setClosed] = useState(false);
  const closeCourse = useMutation({
    mutationFn: () => contentApi.closeCourseVideoAccess(batchId),
    onSuccess: () => setClosed(true),
  });
  const videos = useQuery({
    queryKey: ["videos", batchId],
    queryFn: () => contentApi.listVideos(batchId || undefined),
  });
  const materials = useQuery({
    queryKey: ["materials", batchId],
    queryFn: () => contentApi.listMaterials(batchId || undefined),
  });

  const toast = useToast();
  const [vTitle, setVTitle] = useState("");
  const [vFile, setVFile] = useState<File | null>(null);
  const [mTitle, setMTitle] = useState("");
  const [mFile, setMFile] = useState<File | null>(null);

  const uploadVideo = useMutation({
    mutationFn: () => contentApi.uploadVideo(batchId, vTitle, vFile!),
    onSuccess: () => {
      setVTitle("");
      setVFile(null);
      qc.invalidateQueries({ queryKey: ["videos"] });
      toast.show("Video uploaded — students notified.", "success");
    },
  });
  const uploadMaterial = useMutation({
    mutationFn: () => contentApi.uploadMaterial(batchId, mTitle, mFile!),
    onSuccess: () => {
      setMTitle("");
      setMFile(null);
      qc.invalidateQueries({ queryKey: ["materials"] });
      toast.show("Note uploaded.", "success");
    },
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Content"
        subtitle="Upload and manage class videos and study notes per batch."
      />

      <Card className="mb-6">
        <label htmlFor="content-batch" className="mb-1 block text-sm text-muted">
          Batch
        </label>
        <Select id="content-batch" value={batchId} onChange={(e) => setBatchId(e.target.value)}>
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
          {canUploadVideo && (
            <Card>
              <h2 className="mb-3 text-base font-medium text-ink">Upload class video</h2>
              <div className="flex flex-col gap-2">
                <Input placeholder="Title" value={vTitle} onChange={(e) => setVTitle(e.target.value)} />
                <FileUpload
                  accept="video/*"
                  file={vFile}
                  onFile={setVFile}
                  hint="MP4, WebM or MOV — up to 512 MB"
                />
                <Button
                  onClick={() => uploadVideo.mutate()}
                  disabled={!vTitle || !vFile || uploadVideo.isPending}
                >
                  {uploadVideo.isPending ? "Uploading…" : "Upload video"}
                </Button>
              </div>
            </Card>
          )}

          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">Upload note / material</h2>
            <div className="flex flex-col gap-2">
              <Input placeholder="Title" value={mTitle} onChange={(e) => setMTitle(e.target.value)} />
              <FileUpload
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.zip"
                file={mFile}
                onFile={setMFile}
                hint="PDF, docs, slides or images — up to 25 MB"
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

      {batchId && isMis && (
        <Card className="mb-6">
          <h2 className="mb-1 text-base font-medium text-ink">Video access</h2>
          <p className="mb-3 text-sm text-muted">
            MIS can close this course&apos;s video access at course end (also closes automatically
            when the batch is completed).
          </p>
          {closed ? (
            <span className="text-sm text-[color:var(--color-text-success,#1E8E5A)]">
              ✓ Course video access closed.
            </span>
          ) : (
            <Button variant="ghost" onClick={() => closeCourse.mutate()} disabled={closeCourse.isPending}>
              Close course video access
            </Button>
          )}
        </Card>
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
          <EmptyState title="No videos yet" hint="Faculty upload class recordings here." />
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
          <EmptyState title="No notes yet" />
        )}
      </Card>
    </PortalLayout>
  );
}

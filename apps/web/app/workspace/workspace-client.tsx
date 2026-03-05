"use client";

import type { FileStatus, FileSummary } from "@private-llm/shared-types";
import { ChangeEvent, DragEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { deleteFile, listFiles, reprocessFile, uploadFile } from "../../lib/api";
import { AuthSession, clearSession, readSession, saveSession } from "../../lib/session";

type UploadJob = {
  id: string;
  fileName: string;
  state: "queued" | "uploading" | "uploaded" | "failed";
  message: string;
};

const STATUS_OPTIONS: Array<{ value: FileStatus | ""; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "uploaded", label: "Uploaded" },
  { value: "queued", label: "Queued" },
  { value: "parsing", label: "Parsing" },
  { value: "OCR_fallback", label: "OCR fallback" },
  { value: "chunking", label: "Chunking" },
  { value: "embedding", label: "Embedding" },
  { value: "indexed", label: "Indexed" },
  { value: "failed", label: "Failed" },
  { value: "deleting", label: "Deleting" },
  { value: "deleted", label: "Deleted" }
];

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function normalizeStatus(status: string): string {
  return status.replace(/_/g, " ");
}

export default function WorkspaceClientPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [files, setFiles] = useState<FileSummary[]>([]);
  const [search, setSearch] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<FileStatus | "">("");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadJobs, setUploadJobs] = useState<UploadJob[]>([]);

  useEffect(() => {
    const current = readSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    setSession(current);
  }, [router]);

  async function loadFiles(target: AuthSession) {
    setIsLoading(true);
    setError(null);
    try {
      const rows = await listFiles(target, {
        search: search.trim() || undefined,
        status: selectedStatus,
        includeDeleted
      });
      setFiles(rows);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to load files");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!session) {
      return;
    }
    void loadFiles(session);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, selectedStatus, includeDeleted]);

  async function onSearchSubmit() {
    if (!session) {
      return;
    }
    await loadFiles(session);
  }

  async function onWorkspaceChange(event: ChangeEvent<HTMLSelectElement>) {
    if (!session) {
      return;
    }
    const next = { ...session, activeWorkspaceId: event.target.value };
    saveSession(next);
    setSession(next);
    await loadFiles(next);
  }

  async function onUpload(filesToUpload: File[]) {
    if (!session || filesToUpload.length === 0) {
      return;
    }

    for (const item of filesToUpload) {
      const jobId = `${item.name}-${item.size}-${Date.now()}`;
      setUploadJobs((previous) => [
        {
          id: jobId,
          fileName: item.name,
          state: "queued",
          message: "Waiting to upload"
        },
        ...previous
      ]);

      try {
        setUploadJobs((previous) =>
          previous.map((row) =>
            row.id === jobId ? { ...row, state: "uploading", message: "Uploading..." } : row
          )
        );

        const response = await uploadFile(session, item);
        setUploadJobs((previous) =>
          previous.map((row) =>
            row.id === jobId
              ? {
                  ...row,
                  state: "uploaded",
                  message: `${response.status}: ${response.message}`
                }
              : row
          )
        );
      } catch (cause) {
        setUploadJobs((previous) =>
          previous.map((row) =>
            row.id === jobId
              ? {
                  ...row,
                  state: "failed",
                  message: cause instanceof Error ? cause.message : "Upload failed"
                }
              : row
          )
        );
      }
    }

    await loadFiles(session);
  }

  async function onFileInput(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files;
    if (!selected) {
      return;
    }
    await onUpload(Array.from(selected));
    event.target.value = "";
  }

  async function onReprocess(fileId: string) {
    if (!session) {
      return;
    }
    await reprocessFile(session, fileId);
    await loadFiles(session);
  }

  async function onDelete(fileId: string) {
    if (!session) {
      return;
    }
    await deleteFile(session, fileId);
    await loadFiles(session);
  }

  const recentUploads = useMemo(() => uploadJobs.slice(0, 8), [uploadJobs]);

  return (
    <main className="page-wrap">
      <div
        className="surface"
        style={{
          display: "grid",
          gridTemplateColumns: "260px minmax(0, 1fr)",
          gap: 20,
          padding: 16
        }}
      >
        <aside style={{ borderRight: "1px solid var(--line)", paddingRight: 14 }}>
          <h2 style={{ margin: "4px 0 4px", fontSize: 22 }}>Workspace</h2>
          <p style={{ marginTop: 0, color: "var(--ink-muted)" }}>
            Protected shell for upload and document library workflows.
          </p>

          <label style={{ display: "grid", gap: 8, marginBottom: 14 }}>
            <span style={{ fontSize: 13, color: "var(--ink-muted)" }}>Active workspace</span>
            <select
              className="field"
              value={session?.activeWorkspaceId ?? ""}
              onChange={onWorkspaceChange}
              disabled={!session}
            >
              {(session?.workspaceIds ?? []).map((workspaceId) => (
                <option key={workspaceId} value={workspaceId}>
                  {workspaceId}
                </option>
              ))}
            </select>
          </label>

          <button
            className="button ghost"
            onClick={() => {
              clearSession();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
          <nav style={{ display: "grid", gap: 8, marginTop: 12 }}>
            <Link href="/workspace" className="button brand" style={{ textDecoration: "none", textAlign: "center" }}>
              Document Library
            </Link>
            <Link href="/chat" className="button ghost" style={{ textDecoration: "none", textAlign: "center" }}>
              Chat
            </Link>
            <Link href="/admin" className="button ghost" style={{ textDecoration: "none", textAlign: "center" }}>
              Admin
            </Link>
          </nav>
        </aside>

        <section style={{ display: "grid", gap: 14 }}>
          <header style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            <h1 style={{ margin: 0, fontSize: 30, lineHeight: 1.1 }}>Document Library</h1>
            <span style={{ marginLeft: "auto", color: "var(--ink-muted)" }}>
              {session?.email ?? "loading..."}
            </span>
          </header>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 170px auto auto", gap: 8 }}>
            <input
              className="field"
              placeholder="Search files..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <select
              className="field"
              value={selectedStatus}
              onChange={(event) => setSelectedStatus(event.target.value as FileStatus | "")}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.label} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={includeDeleted}
                onChange={(event) => setIncludeDeleted(event.target.checked)}
              />
              Include deleted
            </label>
            <button className="button" onClick={() => void onSearchSubmit()}>
              Apply
            </button>
          </div>

          <label
            className="surface"
            onDragOver={(event: DragEvent<HTMLLabelElement>) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event: DragEvent<HTMLLabelElement>) => {
              event.preventDefault();
              setIsDragging(false);
              void onUpload(Array.from(event.dataTransfer.files));
            }}
            style={{
              borderStyle: "dashed",
              borderWidth: 2,
              borderColor: isDragging ? "var(--brand)" : "var(--line)",
              borderRadius: 16,
              padding: 18,
              display: "grid",
              gap: 8,
              cursor: "pointer"
            }}
          >
            <strong>Drag and drop files to upload</strong>
            <span style={{ color: "var(--ink-muted)" }}>
              Or click this panel to pick multiple files. Uploads are queued asynchronously.
            </span>
            <input type="file" multiple style={{ display: "none" }} onChange={onFileInput} />
          </label>

          <section className="surface" style={{ padding: 14 }}>
            <h3 style={{ marginTop: 0 }}>Upload Queue</h3>
            {recentUploads.length === 0 ? (
              <p style={{ margin: 0, color: "var(--ink-muted)" }}>No uploads yet.</p>
            ) : (
              <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
                {recentUploads.map((job) => (
                  <li
                    key={job.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                      padding: "8px 10px",
                      borderRadius: 10,
                      background: "var(--surface-muted)"
                    }}
                  >
                    <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: 13 }}>{job.fileName}</span>
                    <span style={{ color: "var(--ink-muted)", fontSize: 13 }}>
                      {job.state}: {job.message}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="surface" style={{ padding: 14, overflowX: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Files</h3>
            {error ? (
              <p role="alert" style={{ color: "var(--danger)" }}>
                {error}
              </p>
            ) : null}
            {isLoading ? <p>Loading files...</p> : null}
            {!isLoading && files.length === 0 ? <p style={{ color: "var(--ink-muted)" }}>No files found.</p> : null}

            {files.length > 0 ? (
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "var(--ink-muted)" }}>
                    <th style={{ padding: "8px 6px" }}>File</th>
                    <th style={{ padding: "8px 6px" }}>Status</th>
                    <th style={{ padding: "8px 6px" }}>Uploaded</th>
                    <th style={{ padding: "8px 6px" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.id} style={{ borderTop: "1px solid var(--line)" }}>
                      <td style={{ padding: "10px 6px" }}>
                        <strong>{file.fileName}</strong>
                        <div style={{ fontSize: 12, color: "var(--ink-muted)" }}>{file.id}</div>
                      </td>
                      <td style={{ padding: "10px 6px" }}>
                        <span className={`status-badge ${file.status}`}>{normalizeStatus(file.status)}</span>
                      </td>
                      <td style={{ padding: "10px 6px", color: "var(--ink-muted)" }}>{formatTime(file.uploadedAt)}</td>
                      <td style={{ padding: "10px 6px", display: "flex", gap: 8 }}>
                        <button className="button" onClick={() => void onReprocess(file.id)}>
                          Reprocess
                        </button>
                        <button className="button danger" onClick={() => void onDelete(file.id)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </section>
        </section>
      </div>
    </main>
  );
}

"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AdminIngestionJobRow,
  AdminIngestionLogRow,
  AdminMetricsResponse,
  AdminSettingsResponse,
  getAdminMetrics,
  getAdminSettings,
  listAdminIngestionJobs,
  listAdminIngestionLogs,
  updateAdminSettings
} from "../../lib/api";
import { AuthSession, clearSession, readSession, saveSession } from "../../lib/session";

type SettingsFormState = {
  llmEndpoint: string;
  llmModel: string;
  embeddingModelName: string;
  chunkSize: string;
  chunkOverlap: string;
  maxFileSizeMb: string;
};

function formatTime(value: string | null): string {
  if (!value) {
    return "n/a";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function toFormState(value: AdminSettingsResponse): SettingsFormState {
  return {
    llmEndpoint: value.llmEndpoint,
    llmModel: value.llmModel,
    embeddingModelName: value.embeddingModelName,
    chunkSize: String(value.chunkSize),
    chunkOverlap: String(value.chunkOverlap),
    maxFileSizeMb: String(value.maxFileSizeMb)
  };
}

export default function AdminClientPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [settings, setSettings] = useState<AdminSettingsResponse | null>(null);
  const [formState, setFormState] = useState<SettingsFormState>({
    llmEndpoint: "",
    llmModel: "",
    embeddingModelName: "",
    chunkSize: "",
    chunkOverlap: "",
    maxFileSizeMb: ""
  });
  const [jobs, setJobs] = useState<AdminIngestionJobRow[]>([]);
  const [logs, setLogs] = useState<AdminIngestionLogRow[]>([]);
  const [metrics, setMetrics] = useState<AdminMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);

  useEffect(() => {
    const current = readSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    setSession(current);
  }, [router]);

  async function loadAdminData(target: AuthSession): Promise<void> {
    setIsLoading(true);
    setError(null);
    try {
      const [nextSettings, nextJobs, nextLogs, nextMetrics] = await Promise.all([
        getAdminSettings(target),
        listAdminIngestionJobs(target, { limit: 120 }),
        listAdminIngestionLogs(target, 120),
        getAdminMetrics(target)
      ]);
      setSettings(nextSettings);
      setFormState(toFormState(nextSettings));
      setJobs(nextJobs);
      setLogs(nextLogs);
      setMetrics(nextMetrics);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to load admin data");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!session) {
      return;
    }
    void loadAdminData(session);
  }, [session]);

  async function onWorkspaceChange(event: ChangeEvent<HTMLSelectElement>): Promise<void> {
    if (!session) {
      return;
    }
    const next = { ...session, activeWorkspaceId: event.target.value };
    saveSession(next);
    setSession(next);
    await loadAdminData(next);
  }

  function onFormChange(event: ChangeEvent<HTMLInputElement>): void {
    const { name, value } = event.target;
    setFormState((previous) => ({ ...previous, [name]: value }));
  }

  async function onSettingsSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!session) {
      return;
    }

    setIsSavingSettings(true);
    setSettingsMessage(null);
    setError(null);
    try {
      const updated = await updateAdminSettings(session, {
        llmEndpoint: formState.llmEndpoint.trim(),
        llmModel: formState.llmModel.trim(),
        embeddingModelName: formState.embeddingModelName.trim(),
        chunkSize: Number(formState.chunkSize),
        chunkOverlap: Number(formState.chunkOverlap),
        maxFileSizeMb: Number(formState.maxFileSizeMb)
      });
      setSettings(updated);
      setFormState(toFormState(updated));
      setSettingsMessage("Settings saved to runtime configuration.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to update settings");
    } finally {
      setIsSavingSettings(false);
    }
  }

  const statusMetrics = useMemo(() => {
    if (!metrics) {
      return [];
    }
    return Object.entries(metrics.statusCounts).sort((left, right) => right[1] - left[1]);
  }, [metrics]);

  return (
    <main className="page-wrap">
      <div className="surface admin-shell">
        <aside className="admin-sidebar">
          <h2 style={{ margin: "4px 0", fontSize: 22 }}>Workspace</h2>
          <p style={{ marginTop: 0, color: "var(--ink-muted)" }}>Admin controls, observability, and resilience view.</p>
          <label style={{ display: "grid", gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 13, color: "var(--ink-muted)" }}>Active workspace</span>
            <select className="field" value={session?.activeWorkspaceId ?? ""} onChange={onWorkspaceChange}>
              {(session?.workspaceIds ?? []).map((workspaceId) => (
                <option key={workspaceId} value={workspaceId}>
                  {workspaceId}
                </option>
              ))}
            </select>
          </label>

          <nav style={{ display: "grid", gap: 8, marginBottom: 12 }}>
            <Link href="/workspace" className="button ghost" style={{ textDecoration: "none", textAlign: "center" }}>
              Document Library
            </Link>
            <Link href="/chat" className="button ghost" style={{ textDecoration: "none", textAlign: "center" }}>
              Chat
            </Link>
            <Link href="/admin" className="button brand" style={{ textDecoration: "none", textAlign: "center" }}>
              Admin
            </Link>
          </nav>

          <button
            className="button ghost"
            onClick={() => {
              clearSession();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
        </aside>

        <section className="admin-main">
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <h1 style={{ margin: 0, fontSize: 30 }}>Admin Console</h1>
            <span style={{ color: "var(--ink-muted)" }}>{session?.email ?? "loading..."}</span>
          </header>

          {isLoading ? <p>Loading admin data...</p> : null}
          {error ? (
            <p role="alert" style={{ margin: 0, color: "var(--danger)" }}>
              {error}
            </p>
          ) : null}

          <section className="surface admin-panel">
            <h3 style={{ marginTop: 0 }}>Model and Parsing Settings</h3>
            <form onSubmit={onSettingsSubmit} className="admin-form-grid">
              <label style={{ display: "grid", gap: 6 }}>
                <span>LLM endpoint</span>
                <input className="field" name="llmEndpoint" value={formState.llmEndpoint} onChange={onFormChange} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>LLM model</span>
                <input className="field" name="llmModel" value={formState.llmModel} onChange={onFormChange} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Embedding model</span>
                <input
                  className="field"
                  name="embeddingModelName"
                  value={formState.embeddingModelName}
                  onChange={onFormChange}
                />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Chunk size</span>
                <input className="field" name="chunkSize" value={formState.chunkSize} onChange={onFormChange} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Chunk overlap</span>
                <input className="field" name="chunkOverlap" value={formState.chunkOverlap} onChange={onFormChange} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Max file size MB</span>
                <input
                  className="field"
                  name="maxFileSizeMb"
                  value={formState.maxFileSizeMb}
                  onChange={onFormChange}
                />
              </label>
              <div style={{ display: "grid", alignContent: "end" }}>
                <button className="button brand" type="submit" disabled={isSavingSettings}>
                  {isSavingSettings ? "Saving..." : "Save settings"}
                </button>
              </div>
            </form>
            {settingsMessage ? <p style={{ marginBottom: 0, color: "var(--success)" }}>{settingsMessage}</p> : null}
            {settings ? (
              <p style={{ marginBottom: 0, color: "var(--ink-muted)" }}>
                Runtime config loaded. Effective chunking: {settings.chunkSize}/{settings.chunkOverlap}.
              </p>
            ) : null}
          </section>

          <section className="admin-metric-grid">
            <article className="surface admin-panel">
              <h3 style={{ marginTop: 0 }}>Stage Timing</h3>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                <li>Queue depth: {metrics?.queueDepth ?? 0}</li>
                <li>Avg queue age: {metrics?.stageTiming.avgQueueAgeSeconds ?? "n/a"}s</li>
                <li>Oldest queue age: {metrics?.stageTiming.oldestQueueAgeSeconds ?? "n/a"}s</li>
                <li>Avg in-flight age: {metrics?.stageTiming.avgInFlightAgeSeconds ?? "n/a"}s</li>
              </ul>
            </article>
            <article className="surface admin-panel">
              <h3 style={{ marginTop: 0 }}>Answer and Request Metrics</h3>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                <li>Uploads: {metrics?.uploadsTotal ?? 0}</li>
                <li>Chat queries: {metrics?.chatQueryCount ?? 0}</li>
                <li>Upload-and-ask requests: {metrics?.uploadAndAskCount ?? 0}</li>
                <li>Answers generated: {metrics?.answersGeneratedCount ?? 0}</li>
                <li>Answers with citations: {metrics?.answersWithCitationsPercent ?? 0}%</li>
              </ul>
            </article>
            <article className="surface admin-panel">
              <h3 style={{ marginTop: 0 }}>File Status Counts</h3>
              {statusMetrics.length === 0 ? (
                <p style={{ margin: 0, color: "var(--ink-muted)" }}>No status data yet.</p>
              ) : (
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {statusMetrics.map(([status, count]) => (
                    <li key={status}>
                      {status}: {count}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </section>

          <section className="surface admin-panel" style={{ overflowX: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Ingestion Jobs</h3>
            {jobs.length === 0 ? (
              <p style={{ margin: 0, color: "var(--ink-muted)" }}>No jobs yet.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 880 }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "var(--ink-muted)" }}>
                    <th style={{ padding: "8px 6px" }}>File</th>
                    <th style={{ padding: "8px 6px" }}>Status</th>
                    <th style={{ padding: "8px 6px" }}>Uploaded</th>
                    <th style={{ padding: "8px 6px" }}>Queue</th>
                    <th style={{ padding: "8px 6px" }}>Last action</th>
                    <th style={{ padding: "8px 6px" }}>Retry</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((row) => (
                    <tr key={row.fileId} style={{ borderTop: "1px solid var(--line)" }}>
                      <td style={{ padding: "10px 6px" }}>
                        <strong>{row.fileName}</strong>
                        <div style={{ fontSize: 12, color: "var(--ink-muted)" }}>{row.fileId}</div>
                      </td>
                      <td style={{ padding: "10px 6px" }}>
                        <span className={`status-badge ${row.status}`}>{row.status.replace(/_/g, " ")}</span>
                      </td>
                      <td style={{ padding: "10px 6px", color: "var(--ink-muted)" }}>{formatTime(row.uploadedAt)}</td>
                      <td style={{ padding: "10px 6px", color: "var(--ink-muted)" }}>
                        {row.queueJobId ? `${row.queueJobId} (${formatTime(row.enqueuedAt)})` : "n/a"}
                      </td>
                      <td style={{ padding: "10px 6px", color: "var(--ink-muted)" }}>
                        {row.lastAction ? `${row.lastAction} (${formatTime(row.lastActionAt)})` : "n/a"}
                      </td>
                      <td style={{ padding: "10px 6px", color: row.retryEligible ? "var(--danger)" : "var(--ink-muted)" }}>
                        {row.retryEligible ? "Retry with reprocess" : "Not required"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="surface admin-panel" style={{ overflowX: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Ingestion and Audit Logs</h3>
            {logs.length === 0 ? (
              <p style={{ margin: 0, color: "var(--ink-muted)" }}>No logs yet.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 800 }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "var(--ink-muted)" }}>
                    <th style={{ padding: "8px 6px" }}>Time</th>
                    <th style={{ padding: "8px 6px" }}>Action</th>
                    <th style={{ padding: "8px 6px" }}>Entity</th>
                    <th style={{ padding: "8px 6px" }}>Metadata</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice(0, 40).map((row) => (
                    <tr key={row.id} style={{ borderTop: "1px solid var(--line)" }}>
                      <td style={{ padding: "10px 6px", color: "var(--ink-muted)" }}>{formatTime(row.createdAt)}</td>
                      <td style={{ padding: "10px 6px" }}>{row.action}</td>
                      <td style={{ padding: "10px 6px", color: "var(--ink-muted)" }}>
                        {row.entityType}
                        {row.entityId ? ` (${row.entityId})` : ""}
                      </td>
                      <td
                        style={{
                          padding: "10px 6px",
                          fontSize: 12,
                          color: "var(--ink-muted)",
                          fontFamily: "var(--font-mono), monospace"
                        }}
                      >
                        {JSON.stringify(row.metadata)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

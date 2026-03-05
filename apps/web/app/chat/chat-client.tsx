"use client";

import type { CitationResponse, PendingRequestStatus, UploadAndAskScope } from "@private-llm/shared-types";
import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChatMessageResponse,
  ChatSessionSummary,
  UploadAndAskStatusResponse,
  createChatSession,
  createUploadAndAskRequest,
  getChatSession,
  getUploadAndAskRequest,
  listChatSessions,
  listFiles,
  queryChat
} from "../../lib/api";
import { AuthSession, clearSession, readSession, saveSession } from "../../lib/session";

type ThreadMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations: CitationResponse[];
  isError?: boolean;
};

type CancelToken = {
  cancelled: boolean;
};

const TERMINAL_PENDING_STATUSES: PendingRequestStatus[] = ["completed", "failed", "cancelled"];

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function renderPendingStatusLabel(status: PendingRequestStatus): string {
  switch (status) {
    case "waiting_for_index":
      return "Waiting for indexing";
    case "executing":
      return "Generating answer";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
    default:
      return status;
  }
}

function mapMessages(rows: ChatMessageResponse[]): ThreadMessage[] {
  return rows.map((row) => ({
    id: row.id,
    role: row.role,
    content: row.content,
    createdAt: row.createdAt,
    citations: []
  }));
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

export default function ChatClientPage() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);

  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ThreadMessage[]>([]);

  const [isLoadingShell, setIsLoadingShell] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const [queryText, setQueryText] = useState("");
  const [scope, setScope] = useState<UploadAndAskScope>("workspace");
  const [indexedFileOptions, setIndexedFileOptions] = useState<Array<{ id: string; fileName: string }>>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);

  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<CitationResponse | null>(null);

  const [groundedError, setGroundedError] = useState<string | null>(null);
  const [shellError, setShellError] = useState<string | null>(null);

  const [uploadAskQuery, setUploadAskQuery] = useState("");
  const [uploadAskFiles, setUploadAskFiles] = useState<File[]>([]);
  const [uploadAskRequestId, setUploadAskRequestId] = useState<string | null>(null);
  const [uploadAskStatus, setUploadAskStatus] = useState<UploadAndAskStatusResponse | null>(null);
  const [uploadAskInfo, setUploadAskInfo] = useState<string | null>(null);
  const [uploadAskError, setUploadAskError] = useState<string | null>(null);
  const [isSubmittingUploadAsk, setIsSubmittingUploadAsk] = useState(false);
  const [uploadInputKey, setUploadInputKey] = useState(0);

  const canSend = useMemo(() => {
    const hasQuery = queryText.trim().length > 0;
    const hasScopeFiles = scope === "workspace" || selectedFileIds.length > 0;
    return hasQuery && hasScopeFiles && !isSending;
  }, [queryText, scope, selectedFileIds.length, isSending]);

  useEffect(() => {
    const current = readSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    setSession(current);
  }, [router]);

  useEffect(() => {
    if (!session) {
      return;
    }

    const cancelToken: CancelToken = { cancelled: false };
    async function bootstrap(target: AuthSession) {
      setIsLoadingShell(true);
      setShellError(null);
      try {
        const [sessionRows, fileRows] = await Promise.all([
          listChatSessions(target),
          listFiles(target, { includeDeleted: false })
        ]);
        if (cancelToken.cancelled) {
          return;
        }
        setChatSessions(sessionRows);
        setIndexedFileOptions(
          fileRows
            .filter((row) => row.status === "indexed")
            .map((row) => ({ id: row.id, fileName: row.fileName }))
        );
        setSelectedFileIds((previous) =>
          previous.filter((fileId) => fileRows.some((row) => row.id === fileId && row.status === "indexed"))
        );

        const firstSession = sessionRows[0];
        if (firstSession) {
          setActiveSessionId(firstSession.id);
          await loadSessionMessages(target, firstSession.id, cancelToken);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      } catch (cause) {
        if (!cancelToken.cancelled) {
          setShellError(cause instanceof Error ? cause.message : "Failed to load chat workspace");
        }
      } finally {
        if (!cancelToken.cancelled) {
          setIsLoadingShell(false);
        }
      }
    }

    void bootstrap(session);
    return () => {
      cancelToken.cancelled = true;
    };
  }, [session]);

  useEffect(() => {
    if (!session || !uploadAskRequestId) {
      return;
    }

    let cancelled = false;
    let pollTimer: number | null = null;

    const poll = async () => {
      try {
        const status = await getUploadAndAskRequest(session, uploadAskRequestId);
        if (cancelled) {
          return;
        }
        setUploadAskStatus(status);
        setUploadAskError(null);
        if (TERMINAL_PENDING_STATUSES.includes(status.status)) {
          if (pollTimer) {
            window.clearInterval(pollTimer);
            pollTimer = null;
          }
        }
      } catch (cause) {
        if (cancelled) {
          return;
        }
        setUploadAskError(cause instanceof Error ? cause.message : "Failed to check upload-and-ask status");
        if (pollTimer) {
          window.clearInterval(pollTimer);
          pollTimer = null;
        }
      }
    };

    void poll();
    pollTimer = window.setInterval(() => {
      void poll();
    }, 1500);

    return () => {
      cancelled = true;
      if (pollTimer) {
        window.clearInterval(pollTimer);
      }
    };
  }, [session, uploadAskRequestId]);

  useEffect(() => {
    const allowed = new Set(indexedFileOptions.map((row) => row.id));
    setSelectedFileIds((previous) => previous.filter((id) => allowed.has(id)));
  }, [indexedFileOptions]);

  const selectedMessage = useMemo(() => {
    if (!selectedMessageId) {
      return null;
    }
    return messages.find((message) => message.id === selectedMessageId) ?? null;
  }, [messages, selectedMessageId]);

  const sidebarCitations = useMemo(() => {
    if (selectedMessage && selectedMessage.citations.length > 0) {
      return selectedMessage.citations;
    }
    if (uploadAskStatus?.citations?.length) {
      return uploadAskStatus.citations;
    }
    return [];
  }, [selectedMessage, uploadAskStatus]);

  useEffect(() => {
    if (sidebarCitations.length === 0) {
      setActiveCitation(null);
      return;
    }
    if (activeCitation && sidebarCitations.some((item) => item.chunkId === activeCitation.chunkId)) {
      return;
    }
    setActiveCitation(sidebarCitations[0] ?? null);
  }, [sidebarCitations, activeCitation]);

  async function refreshSessions(target: AuthSession): Promise<void> {
    const rows = await listChatSessions(target);
    setChatSessions(rows);
  }

  async function refreshIndexedFiles(target: AuthSession): Promise<void> {
    const rows = await listFiles(target, { includeDeleted: false });
    setIndexedFileOptions(
      rows
        .filter((row) => row.status === "indexed")
        .map((row) => ({ id: row.id, fileName: row.fileName }))
    );
  }

  async function loadSessionMessages(target: AuthSession, sessionId: string, cancelToken?: CancelToken): Promise<void> {
    setIsLoadingMessages(true);
    setGroundedError(null);
    try {
      const detail = await getChatSession(target, sessionId);
      if (cancelToken?.cancelled) {
        return;
      }
      const next = mapMessages(detail.messages);
      setMessages(next);
      const lastAssistant = [...next].reverse().find((row) => row.role === "assistant");
      setSelectedMessageId(lastAssistant?.id ?? null);
    } catch (cause) {
      if (!cancelToken?.cancelled) {
        setGroundedError(cause instanceof Error ? cause.message : "Failed to load chat messages");
      }
    } finally {
      if (!cancelToken?.cancelled) {
        setIsLoadingMessages(false);
      }
    }
  }

  async function onWorkspaceChange(event: ChangeEvent<HTMLSelectElement>): Promise<void> {
    if (!session) {
      return;
    }
    const nextSession = { ...session, activeWorkspaceId: event.target.value };
    saveSession(nextSession);
    setSession(nextSession);
    setChatSessions([]);
    setActiveSessionId(null);
    setMessages([]);
    setGroundedError(null);
    setUploadAskStatus(null);
    setUploadAskRequestId(null);
  }

  async function onCreateSession(): Promise<void> {
    if (!session) {
      return;
    }
    setGroundedError(null);
    try {
      const created = await createChatSession(session);
      setChatSessions((previous) => [created, ...previous.filter((row) => row.id !== created.id)]);
      setActiveSessionId(created.id);
      setMessages([]);
      setSelectedMessageId(null);
      setActiveCitation(null);
    } catch (cause) {
      setGroundedError(cause instanceof Error ? cause.message : "Failed to create chat session");
    }
  }

  async function onOpenSession(sessionId: string): Promise<void> {
    if (!session) {
      return;
    }
    setActiveSessionId(sessionId);
    await loadSessionMessages(session, sessionId);
  }

  async function streamAssistantMessage(
    messageId: string,
    finalText: string,
    citations: CitationResponse[],
    isError = false
  ): Promise<void> {
    const words = finalText.trim().split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      setMessages((previous) =>
        previous.map((row) =>
          row.id === messageId ? { ...row, content: finalText, citations, isError } : row
        )
      );
      return;
    }

    let partial = "";
    for (const word of words) {
      partial = partial.length > 0 ? `${partial} ${word}` : word;
      setMessages((previous) =>
        previous.map((row) =>
          row.id === messageId ? { ...row, content: partial, citations, isError } : row
        )
      );
      await wait(16);
    }

    setMessages((previous) =>
      previous.map((row) =>
        row.id === messageId ? { ...row, content: finalText, citations, isError } : row
      )
    );
  }

  async function onSubmitQuery(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!session || !canSend) {
      return;
    }

    const nextQuery = queryText.trim();
    if (!nextQuery) {
      return;
    }

    if (scope === "uploaded_files_only" && selectedFileIds.length === 0) {
      setGroundedError("Select at least one indexed file when scope is set to uploaded files only.");
      return;
    }

    setGroundedError(null);
    setIsSending(true);
    setQueryText("");
    let assistantMessageId: string | null = null;

    let targetSessionId = activeSessionId;
    try {
      if (!targetSessionId) {
        const created = await createChatSession(session, nextQuery.slice(0, 80));
        targetSessionId = created.id;
        setActiveSessionId(created.id);
      }

      const stamp = new Date().toISOString();
      const userMessageId = `local_user_${Date.now()}`;
      const localAssistantMessageId = `local_assistant_${Date.now()}_${Math.random().toString(16).slice(2)}`;
      assistantMessageId = localAssistantMessageId;

      setMessages((previous) => [
        ...previous,
        { id: userMessageId, role: "user", content: nextQuery, createdAt: stamp, citations: [] },
        { id: localAssistantMessageId, role: "assistant", content: "", createdAt: stamp, citations: [] }
      ]);
      setSelectedMessageId(localAssistantMessageId);
      setActiveCitation(null);

      const response = await queryChat(session, {
        workspaceId: session.activeWorkspaceId,
        chatSessionId: targetSessionId,
        mode: "grounded",
        query: nextQuery,
        scope,
        fileIds: scope === "uploaded_files_only" ? selectedFileIds : []
      });

      if (response.status !== "completed") {
        await streamAssistantMessage(
          localAssistantMessageId,
          `Request is currently ${renderPendingStatusLabel(response.status)}.`,
          []
        );
      } else {
        await streamAssistantMessage(
          localAssistantMessageId,
          response.answer ?? "No grounded answer was returned.",
          response.citations
        );
      }

      await Promise.all([refreshSessions(session), refreshIndexedFiles(session)]);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Grounded query failed";
      setGroundedError(message);
      const targetAssistantId = assistantMessageId ?? `local_assistant_error_${Date.now()}`;
      if (!assistantMessageId) {
        setMessages((previous) => [
          ...previous,
          {
            id: targetAssistantId,
            role: "assistant",
            content: "",
            createdAt: new Date().toISOString(),
            citations: [],
            isError: true
          }
        ]);
      }
      setSelectedMessageId(targetAssistantId);
      await streamAssistantMessage(targetAssistantId, message, [], true);
    } finally {
      setIsSending(false);
    }
  }

  function onFileScopeSelection(event: ChangeEvent<HTMLSelectElement>): void {
    const next = Array.from(event.target.selectedOptions).map((option) => option.value);
    setSelectedFileIds(next);
  }

  function onUploadAskFiles(event: ChangeEvent<HTMLInputElement>): void {
    const selected = event.target.files;
    if (!selected) {
      return;
    }
    setUploadAskFiles(Array.from(selected));
  }

  async function onUploadAndAsk(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!session) {
      return;
    }

    const normalizedQuery = uploadAskQuery.trim();
    if (!normalizedQuery) {
      setUploadAskError("Query is required for upload-and-ask.");
      return;
    }
    if (uploadAskFiles.length === 0) {
      setUploadAskError("Add at least one file for upload-and-ask.");
      return;
    }

    setUploadAskError(null);
    setUploadAskInfo(null);
    setIsSubmittingUploadAsk(true);
    try {
      const created = await createUploadAndAskRequest(session, {
        query: normalizedQuery,
        files: uploadAskFiles,
        scope: "uploaded_files_only"
      });
      setUploadAskInfo(created.message);
      setUploadAskRequestId(created.requestId);
      setUploadAskStatus(null);
      setUploadAskFiles([]);
      setUploadAskQuery("");
      setUploadInputKey((value) => value + 1);
      await refreshIndexedFiles(session);
    } catch (cause) {
      setUploadAskError(cause instanceof Error ? cause.message : "Upload-and-ask failed");
    } finally {
      setIsSubmittingUploadAsk(false);
    }
  }

  return (
    <main className="page-wrap">
      <div className="surface chat-shell">
        <aside className="chat-sidebar">
          <h2 style={{ margin: "4px 0", fontSize: 22 }}>Workspace</h2>
          <p style={{ marginTop: 0, color: "var(--ink-muted)" }}>Chat and grounded citation workflows.</p>
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

          <nav style={{ display: "grid", gap: 8, marginBottom: 14 }}>
            <Link href="/workspace" className="button ghost" style={{ textDecoration: "none", textAlign: "center" }}>
              Document Library
            </Link>
            <Link href="/chat" className="button brand" style={{ textDecoration: "none", textAlign: "center" }}>
              Chat
            </Link>
          </nav>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <strong>Sessions</strong>
            <button className="button" onClick={() => void onCreateSession()}>
              New
            </button>
          </div>

          {isLoadingShell ? <p style={{ color: "var(--ink-muted)" }}>Loading workspace...</p> : null}
          {shellError ? (
            <p role="alert" style={{ color: "var(--danger)" }}>
              {shellError}
            </p>
          ) : null}
          {!isLoadingShell && chatSessions.length === 0 ? (
            <p style={{ color: "var(--ink-muted)" }}>No sessions yet. Start by sending a question.</p>
          ) : null}

          <ul className="session-list">
            {chatSessions.map((chatSession) => (
              <li key={chatSession.id}>
                <button
                  className={`session-item ${chatSession.id === activeSessionId ? "active" : ""}`}
                  onClick={() => void onOpenSession(chatSession.id)}
                >
                  <strong>{chatSession.title}</strong>
                  <span>{formatTime(chatSession.updatedAt)}</span>
                </button>
              </li>
            ))}
          </ul>

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

        <section className="chat-main">
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <h1 style={{ margin: 0, fontSize: 30 }}>Grounded Chat</h1>
            <span style={{ color: "var(--ink-muted)" }}>{session?.email ?? "loading..."}</span>
          </header>

          {groundedError ? (
            <p role="alert" style={{ margin: 0, color: "var(--danger)" }}>
              {groundedError}
            </p>
          ) : null}

          <section className="surface" style={{ padding: 14, minHeight: 300, overflowY: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Thread</h3>
            {isLoadingMessages ? <p>Loading messages...</p> : null}
            {!isLoadingMessages && messages.length === 0 ? (
              <p style={{ color: "var(--ink-muted)" }}>
                No messages yet. Ask a question using workspace scope or select indexed files.
              </p>
            ) : null}

            <div className="thread-list">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`thread-message ${message.role} ${selectedMessageId === message.id ? "selected" : ""}`}
                  onClick={() => setSelectedMessageId(message.id)}
                >
                  <header className="thread-meta">
                    <strong>{message.role === "assistant" ? "Assistant" : "You"}</strong>
                    <span>{formatTime(message.createdAt)}</span>
                  </header>
                  <p style={{ margin: 0, color: message.isError ? "var(--danger)" : "inherit" }}>
                    {message.content || (isSending && message.role === "assistant" ? "Generating..." : " ")}
                  </p>
                  {message.citations.length > 0 ? (
                    <small style={{ color: "var(--ink-muted)" }}>
                      {message.citations.length} citation{message.citations.length === 1 ? "" : "s"}
                    </small>
                  ) : null}
                </article>
              ))}
            </div>
          </section>

          <form className="surface chat-compose" onSubmit={onSubmitQuery}>
            <h3 style={{ margin: "0 0 10px" }}>Ask a grounded question</h3>
            <textarea
              className="field"
              rows={3}
              placeholder="Ask about indexed documents..."
              value={queryText}
              onChange={(event) => setQueryText(event.target.value)}
            />
            <div className="chat-compose-row">
              <label style={{ display: "grid", gap: 6 }}>
                <span style={{ fontSize: 13, color: "var(--ink-muted)" }}>Scope</span>
                <select
                  className="field"
                  value={scope}
                  onChange={(event) => setScope(event.target.value as UploadAndAskScope)}
                >
                  <option value="workspace">Entire workspace</option>
                  <option value="uploaded_files_only">Selected indexed files only</option>
                </select>
              </label>

              {scope === "uploaded_files_only" ? (
                <label style={{ display: "grid", gap: 6 }}>
                  <span style={{ fontSize: 13, color: "var(--ink-muted)" }}>Indexed files</span>
                  <select className="field" multiple value={selectedFileIds} onChange={onFileScopeSelection}>
                    {indexedFileOptions.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.fileName}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              <div style={{ display: "grid", alignContent: "end" }}>
                <button className="button brand" type="submit" disabled={!canSend}>
                  {isSending ? "Generating..." : "Send"}
                </button>
              </div>
            </div>
          </form>

          <form className="surface chat-compose" onSubmit={onUploadAndAsk}>
            <h3 style={{ margin: "0 0 10px" }}>Upload and Ask</h3>
            <p style={{ margin: "0 0 10px", color: "var(--ink-muted)" }}>
              Upload files and ask the first grounded question in one action. Status updates will poll automatically.
            </p>
            <input
              className="field"
              placeholder="What do these files say?"
              value={uploadAskQuery}
              onChange={(event) => setUploadAskQuery(event.target.value)}
            />
            <input key={uploadInputKey} className="field" type="file" multiple onChange={onUploadAskFiles} />
            <button className="button" type="submit" disabled={isSubmittingUploadAsk}>
              {isSubmittingUploadAsk ? "Submitting..." : "Start upload-and-ask"}
            </button>
            {uploadAskInfo ? <p style={{ margin: 0, color: "var(--success)" }}>{uploadAskInfo}</p> : null}
            {uploadAskError ? (
              <p role="alert" style={{ margin: 0, color: "var(--danger)" }}>
                {uploadAskError}
              </p>
            ) : null}
            {uploadAskStatus ? (
              <div className="upload-status-panel">
                <p style={{ margin: 0 }}>
                  <strong>Status:</strong> {renderPendingStatusLabel(uploadAskStatus.status)}
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Request:</strong> {uploadAskStatus.requestId}
                </p>
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {Object.entries(uploadAskStatus.fileStatuses).map(([fileId, status]) => (
                    <li key={fileId}>
                      {fileId}: {status}
                    </li>
                  ))}
                </ul>
                {uploadAskStatus.errorMessage ? (
                  <p role="alert" style={{ margin: 0, color: "var(--danger)" }}>
                    {uploadAskStatus.errorMessage}
                  </p>
                ) : null}
                {uploadAskStatus.answer ? (
                  <article className="thread-message assistant selected" onClick={() => setSelectedMessageId(null)}>
                    <header className="thread-meta">
                      <strong>Upload-and-ask answer</strong>
                      <span>{formatTime(uploadAskStatus.updatedAt)}</span>
                    </header>
                    <p style={{ margin: 0 }}>{uploadAskStatus.answer}</p>
                    <small style={{ color: "var(--ink-muted)" }}>
                      {uploadAskStatus.citations.length} citation{uploadAskStatus.citations.length === 1 ? "" : "s"}
                    </small>
                  </article>
                ) : null}
              </div>
            ) : null}
          </form>
        </section>

        <aside className="citation-sidebar">
          <h2 style={{ margin: "6px 0 10px", fontSize: 20 }}>Citations</h2>
          {sidebarCitations.length === 0 ? (
            <p style={{ color: "var(--ink-muted)" }}>
              Ask a grounded question to see citations and preview source chunks.
            </p>
          ) : (
            <ul className="citation-list">
              {sidebarCitations.map((citation) => (
                <li key={`${citation.chunkId}-${citation.fileId}`}>
                  <button
                    className={`citation-item ${activeCitation?.chunkId === citation.chunkId ? "active" : ""}`}
                    onClick={() => setActiveCitation(citation)}
                  >
                    <strong>{citation.fileName}</strong>
                    <span>
                      {citation.page ? `Page ${citation.page}` : citation.sheetName ? citation.sheetName : "No page"}
                    </span>
                    <span style={{ color: "var(--ink-muted)" }}>Score: {citation.score.toFixed(2)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>

      {activeCitation ? (
        <section className="surface chunk-drawer">
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
            <h3 style={{ margin: 0 }}>Source Preview</h3>
            <button className="button" onClick={() => setActiveCitation(null)}>
              Close
            </button>
          </header>
          <p style={{ marginBottom: 8 }}>
            <strong>{activeCitation.fileName}</strong> ·{" "}
            {activeCitation.page ? `Page ${activeCitation.page}` : activeCitation.sheetName ?? "No page metadata"}
          </p>
          {activeCitation.sectionHeading ? (
            <p style={{ marginTop: 0, color: "var(--ink-muted)" }}>{activeCitation.sectionHeading}</p>
          ) : null}
          <div className="surface" style={{ padding: 12, borderRadius: 12, boxShadow: "none" }}>
            {activeCitation.snippet}
          </div>
          <p style={{ marginBottom: 0, color: "var(--ink-muted)", fontFamily: "var(--font-mono), monospace" }}>
            chunkId: {activeCitation.chunkId}
          </p>
        </section>
      ) : null}
    </main>
  );
}

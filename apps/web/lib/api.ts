import type {
  ChatQueryRequest,
  ChatQueryResponse,
  CitationResponse,
  FileStatus,
  FileSummary,
  PendingRequestStatus,
  UploadAndAskScope,
  UploadResponse
} from "@private-llm/shared-types";
import type { AuthSession } from "./session";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type LoginResponse = {
  accessToken: string;
  tokenType: string;
  expiresAt: string;
  userId: string;
  email: string;
  workspaceIds: string[];
};

type ProfileResponse = {
  userId: string;
  email: string;
  workspaceIds: string[];
};

type ApiErrorPayload = {
  detail?: string;
};

export type ChatSessionSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

export type ChatMessageResponse = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

export type ChatSessionDetail = {
  id: string;
  title: string;
  workspaceId: string;
  messages: ChatMessageResponse[];
  createdAt: string;
  updatedAt: string;
};

export type UploadAndAskCreateResult = {
  requestId: string;
  status: PendingRequestStatus;
  message: string;
};

export type UploadAndAskStatusResponse = {
  requestId: string;
  workspaceId: string;
  status: PendingRequestStatus;
  scope: UploadAndAskScope;
  query: string;
  fileIds: string[];
  fileStatuses: Record<string, string>;
  answer: string | null;
  citations: CitationResponse[];
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AdminSettingsResponse = {
  llmEndpoint: string;
  llmModel: string;
  embeddingModelName: string;
  chunkSize: number;
  chunkOverlap: number;
  maxFileSizeMb: number;
};

export type AdminSettingsPatchRequest = Partial<AdminSettingsResponse>;

export type AdminIngestionJobRow = {
  fileId: string;
  fileName: string;
  status: FileStatus;
  uploadedAt: string;
  queueJobId: string | null;
  enqueuedAt: string | null;
  lastAction: string | null;
  lastActionAt: string | null;
  errorMessage: string | null;
  retryEligible: boolean;
};

export type AdminIngestionLogRow = {
  id: string;
  action: string;
  entityType: string;
  entityId: string | null;
  createdAt: string;
  metadata: Record<string, unknown>;
};

export type AdminMetricsResponse = {
  statusCounts: Record<string, number>;
  queueDepth: number;
  uploadsTotal: number;
  chatQueryCount: number;
  uploadAndAskCount: number;
  answersGeneratedCount: number;
  answersWithCitationsPercent: number;
  stageTiming: {
    avgQueueAgeSeconds: number | null;
    oldestQueueAgeSeconds: number | null;
    avgInFlightAgeSeconds: number | null;
  };
};

async function parseError(response: Response): Promise<never> {
  let detail = `Request failed with status ${response.status}`;
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload.detail) {
      detail = payload.detail;
    }
  } catch {
    // best effort error parse only
  }
  throw new Error(detail);
}

function authHeaders(session: AuthSession): HeadersInit {
  return {
    Authorization: `Bearer ${session.accessToken}`,
    "X-Workspace-Id": session.activeWorkspaceId
  };
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as LoginResponse;
}

export async function fetchProfile(session: AuthSession): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${session.accessToken}` }
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as ProfileResponse;
}

export type ListFilesOptions = {
  search?: string;
  status?: FileStatus | "";
  includeDeleted?: boolean;
};

export async function listFiles(session: AuthSession, options: ListFilesOptions): Promise<FileSummary[]> {
  const params = new URLSearchParams();
  if (options.search) {
    params.set("search", options.search);
  }
  if (options.status) {
    params.set("status", options.status);
  }
  if (options.includeDeleted) {
    params.set("includeDeleted", "true");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/files?${params.toString()}`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as FileSummary[];
}

export async function uploadFile(session: AuthSession, file: File): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/files/upload`, {
    method: "POST",
    headers: {
      ...authHeaders(session),
      "X-File-Name": file.name,
      "Content-Type": file.type || "application/octet-stream"
    },
    body: await file.arrayBuffer()
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as UploadResponse;
}

export async function reprocessFile(session: AuthSession, fileId: string): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/files/${fileId}/reprocess`, {
    method: "POST",
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as UploadResponse;
}

export async function deleteFile(session: AuthSession, fileId: string): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/files/${fileId}`, {
    method: "DELETE",
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as UploadResponse;
}

export async function createChatSession(session: AuthSession, title?: string): Promise<ChatSessionSummary> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions`, {
    method: "POST",
    headers: {
      ...authHeaders(session),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ title })
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as ChatSessionSummary;
}

export async function listChatSessions(session: AuthSession): Promise<ChatSessionSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as ChatSessionSummary[];
}

export async function getChatSession(session: AuthSession, sessionId: string): Promise<ChatSessionDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as ChatSessionDetail;
}

export async function queryChat(session: AuthSession, payload: ChatQueryRequest): Promise<ChatQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/query`, {
    method: "POST",
    headers: {
      ...authHeaders(session),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as ChatQueryResponse;
}

export async function createUploadAndAskRequest(
  session: AuthSession,
  payload: {
    query: string;
    files: File[];
    scope?: UploadAndAskScope;
  }
): Promise<UploadAndAskCreateResult> {
  const body = new FormData();
  body.set("query", payload.query);
  body.set("scope", payload.scope ?? "uploaded_files_only");
  for (const file of payload.files) {
    body.append("files", file, file.name);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/upload-and-ask`, {
    method: "POST",
    headers: authHeaders(session),
    body
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as UploadAndAskCreateResult;
}

export async function getUploadAndAskRequest(
  session: AuthSession,
  requestId: string
): Promise<UploadAndAskStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/upload-and-ask/${requestId}`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as UploadAndAskStatusResponse;
}

export async function getAdminSettings(session: AuthSession): Promise<AdminSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/settings`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as AdminSettingsResponse;
}

export async function updateAdminSettings(
  session: AuthSession,
  payload: AdminSettingsPatchRequest
): Promise<AdminSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/settings`, {
    method: "PATCH",
    headers: {
      ...authHeaders(session),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as AdminSettingsResponse;
}

export async function listAdminIngestionJobs(
  session: AuthSession,
  options?: { includeDeleted?: boolean; limit?: number }
): Promise<AdminIngestionJobRow[]> {
  const params = new URLSearchParams();
  if (options?.includeDeleted) {
    params.set("includeDeleted", "true");
  }
  if (options?.limit) {
    params.set("limit", String(options.limit));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";

  const response = await fetch(`${API_BASE_URL}/api/v1/admin/ingestion-jobs${suffix}`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as AdminIngestionJobRow[];
}

export async function listAdminIngestionLogs(
  session: AuthSession,
  limit = 100
): Promise<AdminIngestionLogRow[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/ingestion-logs?limit=${limit}`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as AdminIngestionLogRow[];
}

export async function getAdminMetrics(session: AuthSession): Promise<AdminMetricsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/metrics`, {
    headers: authHeaders(session)
  });
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as AdminMetricsResponse;
}

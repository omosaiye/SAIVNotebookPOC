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

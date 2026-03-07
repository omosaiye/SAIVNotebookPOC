import type { ChatMode, FileStatus, PendingRequestStatus, UploadAndAskScope } from "./enums";

export interface CitationResponse {
  fileId: string;
  fileName: string;
  page: number | null;
  sheetName: string | null;
  sectionHeading: string | null;
  snippet: string;
  chunkId: string;
  score: number;
}

export interface FileSummary {
  id: string;
  workspaceId: string;
  fileName: string;
  status: FileStatus;
  uploadedAt: string;
}

export interface FileDetail extends FileSummary {
  mimeType: string;
  sizeBytes: number;
  objectKey: string;
  parserUsed: string | null;
  errorMessage: string | null;
}

export interface UploadResponse {
  fileId: string;
  status: FileStatus;
  message: string;
}

export interface ChatQueryRequest {
  workspaceId: string;
  chatSessionId: string | null;
  mode: ChatMode;
  query: string;
  scope: UploadAndAskScope;
  fileIds: string[];
}

export interface ChatQueryResponse {
  requestId: string;
  status: PendingRequestStatus;
  answer: string | null;
  citations: CitationResponse[];
  pendingRequestId: string | null;
}

export interface PendingUploadAndAskRequestState {
  requestId: string;
  workspaceId: string;
  status: PendingRequestStatus;
  scope: UploadAndAskScope;
  query: string;
  fileIds: string[];
  createdAt: string;
  updatedAt: string;
}

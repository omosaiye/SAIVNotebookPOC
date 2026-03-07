export const FILE_STATUSES = [
  "uploaded",
  "queued",
  "parsing",
  "OCR_fallback",
  "chunking",
  "embedding",
  "indexed",
  "failed",
  "deleting",
  "deleted"
] as const;

export const PENDING_REQUEST_STATUSES = [
  "waiting_for_index",
  "executing",
  "completed",
  "failed",
  "cancelled"
] as const;

export const CHAT_MODES = ["grounded"] as const;

export const UPLOAD_AND_ASK_SCOPES = ["uploaded_files_only", "workspace"] as const;

export type FileStatus = (typeof FILE_STATUSES)[number];
export type PendingRequestStatus = (typeof PENDING_REQUEST_STATUSES)[number];
export type ChatMode = (typeof CHAT_MODES)[number];
export type UploadAndAskScope = (typeof UPLOAD_AND_ASK_SCOPES)[number];

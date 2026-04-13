export type ProcessingStatus = 'pending' | 'processing' | 'processed' | 'failed';
export type ScanStatus = 'pending' | 'clean' | 'suspicious' | 'malicious' | null;
export type AlertLevel = 'info' | 'warning' | 'critical';

export interface FileItem {
  id: string;
  title: string;
  original_name: string;
  mime_type: string;
  size: number;
  processing_status: ProcessingStatus;
  scan_status: ScanStatus;
  scan_details: string | null;
  metadata_json: Record<string, unknown> | null;
  requires_attention: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertItem {
  id: number;
  file_id: string;
  level: AlertLevel;
  message: string;
  created_at: string;
}

/**
 * Generic paginated response type per D-01.
 * Matches backend PaginatedResponse schema.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * API Error codes matching backend error definitions
 */
export type ApiErrorCode =
  | 'file_not_found'
  | 'stored_file_missing'
  | 'empty_upload'
  | 'upload_size_exceeded'
  | 'processing_error'
  | 'validation_error'
  | 'internal_error'
  | 'network_error';

/**
 * Error payload structure from backend error response
 */
export interface ApiErrorPayload {
  code: ApiErrorCode;
  message: string;
  details?: Record<string, unknown> | null;
  fields?: Record<string, string[]> | null;
  retryable: boolean;
  request_id?: string;
}

/**
 * Full error response envelope from backend
 */
export interface ApiErrorResponse {
  error: ApiErrorPayload;
}

import { apiRequest, apiRequestFormData, buildQueryString, API_BASE_URL } from './client';
import { ApiError, parseApiError } from './errors';
import type { FileItem, PaginatedResponse } from './types';

export interface FetchFilesOptions {
  page?: number;
  pageSize?: number;
}

/**
 * Fetch paginated list of files
 */
export async function fetchFiles(
  options: FetchFilesOptions = {}
): Promise<PaginatedResponse<FileItem>> {
  const { page = 1, pageSize = 10 } = options;

  const queryString = buildQueryString({
    page,
    page_size: pageSize,
  });

  return apiRequest<PaginatedResponse<FileItem>>(`/files${queryString}`, {
    cache: 'no-store',
  });
}

/**
 * Upload a file to the server
 */
export async function uploadFile(formData: FormData): Promise<void> {
  try {
    await apiRequestFormData<void>('/files', formData);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error; // Already typed
    }

    // Wrap unexpected errors
    throw new ApiError(
      'internal_error',
      'Не удалось загрузить файл',
      500,
      false
    );
  }
}

/**
 * Fetch a single file by ID
 */
export async function fetchFile(id: string): Promise<FileItem> {
  return apiRequest<FileItem>(`/files/${id}`, {
    cache: 'no-store',
  });
}

/**
 * Delete a file by ID
 */
export async function deleteFile(id: string): Promise<void> {
  return apiRequest<void>(`/files/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Download a file by ID with proper error handling
 */
export async function downloadFile(fileId: string, filename: string): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/files/${fileId}/download`);
    
    if (!response.ok) {
      const error = await parseApiError(response);
      throw error;
    }
    
    // Get blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Wrap network errors
    throw new ApiError('network_error', 'Не удалось скачать файл', 0, true);
  }
}

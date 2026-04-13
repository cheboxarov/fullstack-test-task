import type { ApiErrorCode } from './types';

/**
 * Typed API Error class for backend error handling
 */
export class ApiError extends Error {
  constructor(
    public readonly code: ApiErrorCode,
    message: string,
    public readonly status: number,
    public readonly retryable: boolean,
    public readonly requestId?: string,
    public readonly fields?: Record<string, string[]>,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /**
   * Check if this is a validation error
   */
  isValidationError(): boolean {
    return this.code === 'validation_error';
  }

  /**
   * Check if this is a "not found" error
   */
  isNotFound(): boolean {
    return this.code === 'file_not_found' || this.code === 'stored_file_missing';
  }

  /**
   * Check if this is a network error
   */
  isNetworkError(): boolean {
    return this.code === 'network_error';
  }

  /**
   * Check if this is a server-side processing error
   */
  isProcessingError(): boolean {
    return this.code === 'processing_error';
  }

  /**
   * Get user-friendly error message in Russian
   */
  getUserMessage(): string {
    const messages: Record<ApiErrorCode, string> = {
      file_not_found: 'Файл не найден',
      stored_file_missing: 'Файл отсутствует в хранилище',
      empty_upload: 'Загрузка пустого файла невозможна',
      upload_size_exceeded: 'Размер файла превышает допустимый лимит',
      processing_error: 'Ошибка при обработке файла',
      validation_error: 'Ошибка валидации данных',
      internal_error: 'Внутренняя ошибка сервера',
      network_error: 'Ошибка сети. Проверьте подключение',
    };

    return messages[this.code] || this.message;
  }
}

/**
 * Parse backend error response into typed ApiError
 */
export async function parseApiError(response: Response): Promise<ApiError> {
  const status = response.status;

  try {
    // Try to parse backend error envelope
    const data = await response.json();

    if (data && typeof data === 'object' && 'error' in data) {
      const errorPayload = data.error;

      return new ApiError(
        errorPayload.code || 'internal_error',
        errorPayload.message || 'Произошла ошибка',
        status,
        errorPayload.retryable ?? false,
        errorPayload.request_id,
        errorPayload.fields || undefined,
        errorPayload.details || undefined
      );
    }
  } catch {
    // JSON parsing failed or no error envelope
  }

  // Fallback to generic error based on status code
  const fallbackCode: ApiErrorCode = status >= 500 ? 'internal_error' : 'validation_error';
  const fallbackMessage = status >= 500
    ? 'Внутренняя ошибка сервера'
    : 'Ошибка при обработке запроса';

  return new ApiError(
    fallbackCode,
    fallbackMessage,
    status,
    false
  );
}

/**
 * Wrap unknown errors into ApiError instances
 */
export function wrapError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof Error) {
    // Check for network-related errors
    if (
      error.message.includes('fetch') ||
      error.message.includes('network') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('Failed to fetch')
    ) {
      return new ApiError(
        'network_error',
        'Ошибка сети. Проверьте подключение',
        0,
        true
      );
    }

    return new ApiError(
      'internal_error',
      error.message,
      500,
      false
    );
  }

  return new ApiError(
    'internal_error',
    'Неизвестная ошибка',
    500,
    false
  );
}

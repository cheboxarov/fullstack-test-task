import { apiRequest, buildQueryString } from './client';
import type { AlertItem, PaginatedResponse } from './types';

export interface FetchAlertsOptions {
  page?: number;
  pageSize?: number;
}

/**
 * Fetch paginated list of alerts
 */
export async function fetchAlerts(
  options: FetchAlertsOptions = {}
): Promise<PaginatedResponse<AlertItem>> {
  const { page = 1, pageSize = 10 } = options;

  const queryString = buildQueryString({
    page,
    page_size: pageSize,
  });

  return apiRequest<PaginatedResponse<AlertItem>>(`/alerts${queryString}`, {
    cache: 'no-store',
  });
}

/**
 * Fetch a single alert by ID
 */
export async function fetchAlert(id: number): Promise<AlertItem> {
  return apiRequest<AlertItem>(`/alerts/${id}`, {
    cache: 'no-store',
  });
}

/**
 * Dismiss/acknowledge an alert
 */
export async function dismissAlert(id: number): Promise<void> {
  return apiRequest<void>(`/alerts/${id}/dismiss`, {
    method: 'POST',
  });
}

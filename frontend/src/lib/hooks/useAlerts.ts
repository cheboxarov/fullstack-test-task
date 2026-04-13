"use client";

import { AlertItem } from "../api/types";
import { fetchAlerts } from "../api/alerts";
import { ApiError } from "../api/errors";
import { usePaginatedResource } from "./usePaginatedResource";

interface UseAlertsReturn {
  alerts: AlertItem[];
  isLoading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
  clearError: () => void;
  // Pagination per D-05
  page: number;
  pageSize: number;
  total: number;
  pages: number;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
}

// Stable fetcher function defined outside hook
const alertsFetcher = (page: number, pageSize: number) => fetchAlerts({ page, pageSize });

export function useAlerts(): UseAlertsReturn {
  const {
    items: alerts,
    isLoading,
    error,
    refresh,
    clearError,
    pagination,
    setPage,
    setPageSize,
  } = usePaginatedResource<AlertItem>(alertsFetcher, { defaultPageSize: 10 });

  return {
    alerts,
    isLoading,
    error,
    refresh,
    clearError,
    // Pagination per D-05
    page: pagination.page,
    pageSize: pagination.pageSize,
    total: pagination.total,
    pages: pagination.pages,
    setPage,
    setPageSize,
  };
}

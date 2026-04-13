"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PaginatedResponse } from "../api/types";
import { ApiError, wrapError } from "../api/errors";

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
  pages: number;
}

export interface UsePaginatedResourceOptions {
  defaultPageSize?: number;
}

export interface UsePaginatedResourceReturn<T> {
  items: T[];
  isLoading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
  clearError: () => void;
  pagination: PaginationState;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
}

export function usePaginatedResource<T>(
  fetcher: (page: number, pageSize: number) => Promise<PaginatedResponse<T>>,
  options: UsePaginatedResourceOptions = {}
): UsePaginatedResourceReturn<T> {
  const { defaultPageSize = 10 } = options;

  const [items, setItems] = useState<T[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const [page, setPageState] = useState(1);
  const [pageSize, setPageSizeState] = useState(defaultPageSize);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);

  // Use ref to avoid re-creating refresh when fetcher changes
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetcherRef.current(page, pageSize);
      setItems(response.items);
      setTotal(response.total);
      setPages(response.pages);
    } catch (err) {
      const apiError = wrapError(err);
      setError(apiError);
      // Keep showing stale data during refresh errors
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]); // Removed fetcher from deps

  // Reset to page 1 when page size changes
  const setPageSize = useCallback((newPageSize: number) => {
    setPageSizeState(newPageSize);
    setPageState(1);
  }, []);

  // Clamp page to valid range
  const setPage = useCallback((newPage: number) => {
    setPageState((prev) => {
      const clamped = Math.max(1, newPage);
      return clamped;
    });
  }, []);

  // Sync page if it exceeds total pages after data update
  useEffect(() => {
    if (pages > 0 && page > pages) {
      setPageState(pages);
    }
  }, [page, pages]);

  // Track if component is mounted to prevent state updates after unmount
  const isMountedRef = useRef(true);
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Use ref to track if we need to fetch (on mount or when page/pageSize changes)
  const needsFetchRef = useRef(true);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  
  useEffect(() => {
    needsFetchRef.current = true;
  }, [page, pageSize]);
  
  useEffect(() => {
    if (needsFetchRef.current) {
      needsFetchRef.current = false;
      void refreshRef.current();
    }
  }, [page, pageSize]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    items,
    isLoading,
    error,
    refresh,
    clearError,
    pagination: {
      page,
      pageSize,
      total,
      pages,
    },
    setPage,
    setPageSize,
  };
}

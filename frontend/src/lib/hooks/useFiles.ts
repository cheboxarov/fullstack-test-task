"use client";

import { useCallback, useState } from "react";
import { FileItem } from "../api/types";
import { fetchFiles, uploadFile as apiUploadFile } from "../api/files";
import { ApiError, wrapError } from "../api/errors";
import { usePaginatedResource } from "./usePaginatedResource";

interface UseFilesReturn {
  files: FileItem[];
  isLoading: boolean;
  isUploading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
  uploadFile: (title: string, file: File) => Promise<void>;
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
const filesFetcher = (page: number, pageSize: number) => fetchFiles({ page, pageSize });

export function useFiles(): UseFilesReturn {
  const [isUploading, setIsUploading] = useState(false);

  const {
    items: files,
    isLoading,
    error,
    refresh,
    clearError,
    pagination,
    setPage,
    setPageSize,
  } = usePaginatedResource<FileItem>(filesFetcher, { defaultPageSize: 10 });

  const handleUpload = useCallback(async (title: string, file: File) => {
    setIsUploading(true);

    const formData = new FormData();
    formData.append("title", title.trim());
    formData.append("file", file);

    try {
      await apiUploadFile(formData);
      await refresh();
    } catch (err) {
      const apiError = wrapError(err);
      throw apiError;
    } finally {
      setIsUploading(false);
    }
  }, [refresh]);

  return {
    files,
    isLoading,
    isUploading,
    error,
    refresh,
    uploadFile: handleUpload,
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

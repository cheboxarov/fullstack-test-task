"use client";

import { Button, Badge, Table } from "react-bootstrap";
import { FileItem } from "../../lib/api/types";
import { downloadFile } from "../../lib/api/files";
import { ApiError } from "../../lib/api/errors";
import {
  SectionCard,
  PageSizeSelect,
  LoadingState,
  EmptyState,
  PaginationControls,
} from "../shared/ui";
import {
  formatDate,
  formatSize,
  getProcessingVariant,
} from "../../lib/utils/formatters";

interface FileListProps {
  files: FileItem[];
  isLoading: boolean;
  // Pagination props per D-05, D-06
  page: number;
  pageSize: number;
  total: number;
  pages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  // Download error handler per D-08
  onDownloadError?: (error: ApiError) => void;
}

export function FileList({
  files,
  isLoading,
  page,
  pageSize,
  total,
  pages,
  onPageChange,
  onPageSizeChange,
  onDownloadError,
}: FileListProps) {
  // Calculate displayed range
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  // Handle file download with error handling per D-08
  async function handleDownload(file: FileItem) {
    try {
      await downloadFile(file.id, file.original_name);
    } catch (error) {
      if (error instanceof ApiError) {
        onDownloadError?.(error);
      }
    }
  }

  return (
    <SectionCard
      title="Файлы"
      headerAction={
        <div className="d-flex align-items-center gap-3">
          <PageSizeSelect value={pageSize} onChange={onPageSizeChange} />
          <Badge bg="secondary">{total} всего</Badge>
        </div>
      }
    >
      {/* Show pagination info */}
      {!isLoading && total > 0 && (
        <div className="text-muted small mb-3">
          Показано {startItem}-{endItem} из {total}
        </div>
      )}

      {isLoading ? (
        <LoadingState />
      ) : (
        <div className="table-responsive">
          <Table hover bordered className="align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Название</th>
                <th>Файл</th>
                <th>MIME</th>
                <th>Размер</th>
                <th>Статус</th>
                <th>Проверка</th>
                <th>Создан</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {files.length === 0 ? (
                <EmptyState message="Файлы пока не загружены" colSpan={8} />
              ) : (
                files.map((file) => (
                  <tr key={file.id}>
                    <td>
                      <div className="fw-semibold">{file.title}</div>
                      <div className="small text-secondary">{file.id}</div>
                    </td>
                    <td>{file.original_name}</td>
                    <td>{file.mime_type}</td>
                    <td>{formatSize(file.size)}</td>
                    <td>
                      <Badge bg={getProcessingVariant(file.processing_status)}>
                        {file.processing_status}
                      </Badge>
                    </td>
                    <td>
                      <div className="d-flex flex-column gap-1">
                        <Badge bg={file.requires_attention ? "warning" : "success"}>
                          {file.scan_status ?? "pending"}
                        </Badge>
                        <span className="small text-secondary">
                          {file.scan_details ?? "Ожидает обработки"}
                        </span>
                      </div>
                    </td>
                    <td>{formatDate(file.created_at)}</td>
                    <td className="text-nowrap">
                      <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={() => handleDownload(file)}
                      >
                        Скачать
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </div>
      )}

      <PaginationControls
        page={page}
        pages={pages}
        onPageChange={onPageChange}
      />
    </SectionCard>
  );
}

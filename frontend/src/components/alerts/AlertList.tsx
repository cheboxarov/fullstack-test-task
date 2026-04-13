"use client";

import { Badge } from "react-bootstrap";
import { AlertItem } from "../../lib/api/types";
import {
  SectionCard,
  PageSizeSelect,
  LoadingState,
  EmptyState,
  PaginationControls,
} from "../shared/ui";
import { formatDate, getLevelVariant } from "../../lib/utils/formatters";
import { Table } from "react-bootstrap";

interface AlertListProps {
  alerts: AlertItem[];
  isLoading: boolean;
  // Pagination props
  page: number;
  pageSize: number;
  total: number;
  pages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

export function AlertList({
  alerts,
  isLoading,
  page,
  pageSize,
  total,
  pages,
  onPageChange,
  onPageSizeChange,
}: AlertListProps) {
  // Calculate displayed range
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  return (
    <SectionCard
      title="Алерты"
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
                <th>ID</th>
                <th>File ID</th>
                <th>Уровень</th>
                <th>Сообщение</th>
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length === 0 ? (
                <EmptyState message="Алертов пока нет" colSpan={5} />
              ) : (
                alerts.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td className="small">{item.file_id}</td>
                    <td>
                      <Badge bg={getLevelVariant(item.level)}>{item.level}</Badge>
                    </td>
                    <td>{item.message}</td>
                    <td>{formatDate(item.created_at)}</td>
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

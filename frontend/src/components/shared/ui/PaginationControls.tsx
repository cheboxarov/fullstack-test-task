import { Pagination } from "react-bootstrap";

interface PaginationControlsProps {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export function PaginationControls({ page, pages, onPageChange }: PaginationControlsProps) {
  if (pages <= 1) return null;

  return (
    <div className="d-flex justify-content-center mt-3">
      <Pagination>
        <Pagination.First
          onClick={() => onPageChange(1)}
          disabled={page === 1}
        />
        <Pagination.Prev
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
        />

        {Array.from({ length: pages }, (_, i) => i + 1)
          .filter(
            (p) =>
              p === 1 ||
              p === pages ||
              (p >= page - 1 && p <= page + 1)
          )
          .map((p, idx, arr) => (
            <span key={p} className="d-flex">
              {idx > 0 && p - arr[idx - 1] > 1 && (
                <Pagination.Ellipsis disabled />
              )}
              <Pagination.Item
                active={p === page}
                onClick={() => onPageChange(p)}
              >
                {p}
              </Pagination.Item>
            </span>
          ))}

        <Pagination.Next
          onClick={() => onPageChange(page + 1)}
          disabled={page === pages}
        />
        <Pagination.Last
          onClick={() => onPageChange(pages)}
          disabled={page === pages}
        />
      </Pagination>
    </div>
  );
}

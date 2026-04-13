import { Badge, Form } from "react-bootstrap";
import { ReactNode } from "react";

interface ListHeaderProps {
  title: string;
  total: number;
  pageSize: number;
  onPageSizeChange: (pageSize: number) => void;
  children?: ReactNode;
}

export function ListHeader({ 
  title, 
  total, 
  pageSize, 
  onPageSizeChange,
  children 
}: ListHeaderProps) {
  return (
    <div className="d-flex justify-content-between align-items-center">
      <h2 className="h5 mb-0">{title}</h2>
      <div className="d-flex align-items-center gap-3">
        <Form.Select
          size="sm"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          style={{ width: "auto" }}
        >
          <option value={10}>10 на странице</option>
          <option value={25}>25 на странице</option>
          <option value={50}>50 на странице</option>
        </Form.Select>
        <Badge bg="secondary">{total} всего</Badge>
        {children}
      </div>
    </div>
  );
}

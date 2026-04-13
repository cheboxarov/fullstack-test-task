import { Card } from "react-bootstrap";
import { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  children: ReactNode;
  headerAction?: ReactNode;
}

export function SectionCard({ title, children, headerAction }: SectionCardProps) {
  return (
    <Card className="shadow-sm border-0">
      <Card.Header className="bg-white border-0 pt-4 px-4">
        <div className="d-flex justify-content-between align-items-center">
          <h2 className="h5 mb-0">{title}</h2>
          {headerAction}
        </div>
      </Card.Header>
      <Card.Body className="px-4 pb-4">
        {children}
      </Card.Body>
    </Card>
  );
}

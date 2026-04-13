import { Spinner } from "react-bootstrap";

export function LoadingState() {
  return (
    <div className="d-flex justify-content-center py-5">
      <Spinner animation="border" />
    </div>
  );
}

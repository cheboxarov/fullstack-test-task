"use client";

import { Alert, Button } from "react-bootstrap";
import { ApiError } from "../../../lib/api/errors";

interface ErrorBannerProps {
  error: ApiError | null;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ErrorBanner({ error, onRetry, onDismiss }: ErrorBannerProps) {
  if (!error) return null;

  return (
    <Alert
      variant={error.retryable ? "warning" : "danger"}
      className="shadow-sm mb-3"
      dismissible={!!onDismiss}
      onClose={onDismiss}
    >
      <div className="d-flex justify-content-between align-items-center">
        <span>{error.getUserMessage()}</span>
        {error.retryable && onRetry && (
          <Button variant="outline-warning" size="sm" onClick={onRetry}>
            Повторить
          </Button>
        )}
      </div>
      {error.requestId && (
        <small className="text-muted d-block mt-1">
          Request ID: {error.requestId}
        </small>
      )}
    </Alert>
  );
}

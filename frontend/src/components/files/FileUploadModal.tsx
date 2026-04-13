"use client";

import { FormEvent, useState, useEffect } from "react";
import { Button, Form, Modal, Alert } from "react-bootstrap";
import { ApiError } from "../../lib/api/errors";

interface FileUploadModalProps {
  show: boolean;
  onHide: () => void;
  onSubmit: (title: string, file: File) => Promise<void>;
  isSubmitting: boolean;
  error?: ApiError | null;
  onClearError?: () => void;
}

export function FileUploadModal({
  show,
  onHide,
  onSubmit,
  isSubmitting,
  error,
  onClearError,
}: FileUploadModalProps) {
  const [title, setTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Reset form when modal closes
  useEffect(() => {
    if (!show) {
      setTitle("");
      setSelectedFile(null);
      onClearError?.();
    }
  }, [show, onClearError]);

  // Clear error on form changes
  const handleTitleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTitle(event.target.value);
    if (error && onClearError) {
      onClearError();
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(event.target.files?.[0] ?? null);
    if (error && onClearError) {
      onClearError();
    }
  };

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!title.trim() || !selectedFile) {
      return;
    }

    try {
      await onSubmit(title.trim(), selectedFile);
      // Form will be reset by useEffect when show becomes false
    } catch {
      // Error is handled by parent via error prop
    }
  }

  // Get field-level errors from ApiError
  const titleError = error?.fields?.title?.[0];
  const fileError = error?.fields?.file?.[0];

  return (
    <Modal show={show} onHide={onHide} centered>
      <Form onSubmit={handleSubmit}>
        <Modal.Header closeButton>
          <Modal.Title>Добавить файл</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {/* General error message */}
          {error && !titleError && !fileError && (
            <Alert variant="danger" className="mb-3">
              {error.getUserMessage()}
              {error.requestId && (
                <small className="text-muted d-block mt-1">
                  Request ID: {error.requestId}
                </small>
              )}
            </Alert>
          )}

          <Form.Group className="mb-3">
            <Form.Label>Название</Form.Label>
            <Form.Control
              value={title}
              onChange={handleTitleChange}
              placeholder="Например, Договор с подрядчиком"
              isInvalid={!!titleError}
            />
            {titleError && (
              <Form.Control.Feedback type="invalid">
                {titleError}
              </Form.Control.Feedback>
            )}
          </Form.Group>
          <Form.Group>
            <Form.Label>Файл</Form.Label>
            <Form.Control
              type="file"
              onChange={handleFileChange}
              isInvalid={!!fileError}
            />
            {fileError && (
              <Form.Control.Feedback type="invalid">
                {fileError}
              </Form.Control.Feedback>
            )}
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={onHide}>
            Отмена
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting || !title.trim() || !selectedFile}>
            {isSubmitting ? "Загрузка..." : "Сохранить"}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}

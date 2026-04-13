"use client";

import { useState } from "react";
import { Container, Row, Col, Card, Button, Alert } from "react-bootstrap";
import { useFiles, useAlerts } from "../lib/hooks";
import { ApiError } from "../lib/api/errors";
import { FileList, AlertList, FileUploadModal } from "../components";
import { ErrorBanner } from "../components/shared/ui";

export default function Page() {
  const [showModal, setShowModal] = useState(false);
  const [downloadError, setDownloadError] = useState<ApiError | null>(null);

  // Files with pagination per D-05
  const {
    files,
    isLoading: filesLoading,
    isUploading,
    error: filesError,
    refresh: refreshFiles,
    uploadFile,
    clearError: clearFilesError,
    page: filePage,
    pageSize: filePageSize,
    total: fileTotal,
    pages: filePages,
    setPage: setFilePage,
    setPageSize: setFilePageSize,
  } = useFiles();

  // Alerts with pagination per D-05
  const {
    alerts,
    isLoading: alertsLoading,
    error: alertsError,
    refresh: refreshAlerts,
    clearError: clearAlertsError,
    page: alertPage,
    pageSize: alertPageSize,
    total: alertTotal,
    pages: alertPages,
    setPage: setAlertPage,
    setPageSize: setAlertPageSize,
  } = useAlerts();

  async function handleRefresh() {
    await Promise.all([refreshFiles(), refreshAlerts()]);
  }

  async function handleUpload(title: string, file: File) {
    await uploadFile(title, file);
    setShowModal(false);
  }

  return (
    <Container fluid className="py-4 px-4 bg-light min-vh-100">
      <Row className="justify-content-center">
        <Col xxl={10} xl={11}>
          {/* Header Card */}
          <Card className="shadow-sm border-0 mb-4">
            <Card.Body className="p-4">
              <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                <div>
                  <h1 className="h3 mb-2">Управление файлами</h1>
                  <p className="text-secondary mb-0">
                    Загрузка файлов, просмотр статусов обработки и ленты алертов.
                  </p>
                </div>
                <div className="d-flex gap-2">
                  <Button variant="outline-secondary" onClick={() => void handleRefresh()}>
                    Обновить
                  </Button>
                  <Button variant="primary" onClick={() => setShowModal(true)}>
                    Добавить файл
                  </Button>
                </div>
              </div>
            </Card.Body>
          </Card>

          {/* Files Error Banner */}
          <ErrorBanner
            error={filesError}
            onRetry={filesError?.retryable ? refreshFiles : undefined}
            onDismiss={clearFilesError}
          />

          {/* Alerts Error Banner */}
          <ErrorBanner
            error={alertsError}
            onRetry={alertsError?.retryable ? refreshAlerts : undefined}
            onDismiss={clearAlertsError}
          />

          {/* Download Error Alert per D-08 */}
          {downloadError && (
            <Alert variant="danger" dismissible onClose={() => setDownloadError(null)} className="shadow-sm mb-3">
              {downloadError.message}
              {downloadError.code === 'stored_file_missing' && (
                <div className="small text-muted mt-1">
                  Файл был удалён с диска, но запись осталась в базе
                </div>
              )}
            </Alert>
          )}

          {/* Files Section with pagination */}
          <FileList
            files={files}
            isLoading={filesLoading}
            page={filePage}
            pageSize={filePageSize}
            total={fileTotal}
            pages={filePages}
            onPageChange={setFilePage}
            onPageSizeChange={setFilePageSize}
            onDownloadError={setDownloadError}
          />

          {/* Alerts Section with pagination */}
          <AlertList
            alerts={alerts}
            isLoading={alertsLoading}
            page={alertPage}
            pageSize={alertPageSize}
            total={alertTotal}
            pages={alertPages}
            onPageChange={setAlertPage}
            onPageSizeChange={setAlertPageSize}
          />
        </Col>
      </Row>

      {/* Upload Modal */}
      <FileUploadModal
        show={showModal}
        onHide={() => {
          setShowModal(false);
          clearFilesError();
        }}
        onSubmit={handleUpload}
        isSubmitting={isUploading}
        error={filesError}
        onClearError={clearFilesError}
      />
    </Container>
  );
}

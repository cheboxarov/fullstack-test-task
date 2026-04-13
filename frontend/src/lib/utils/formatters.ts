import type { ProcessingStatus, AlertLevel } from "../api/types";

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function getLevelVariant(level: AlertLevel): string {
  const variants: Record<AlertLevel, string> = {
    info: "info",
    warning: "warning",
    critical: "danger",
  };
  return variants[level] ?? "info";
}

export function getProcessingVariant(status: ProcessingStatus): string {
  const variants: Record<ProcessingStatus, string> = {
    pending: "secondary",
    processing: "warning",
    processed: "success",
    failed: "danger",
  };
  return variants[status] ?? "secondary";
}

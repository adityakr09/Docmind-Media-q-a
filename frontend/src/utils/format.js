/**
 * Format seconds → mm:ss
 */
export function formatTime(secs) {
  if (!secs && secs !== 0) return "—";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Format bytes → human readable
 */
export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Get display label for document status
 */
export function getStatusLabel(status) {
  const map = {
    pending: "Queued",
    processing: "Processing…",
    ready: "Ready",
    failed: "Failed",
  };
  return map[status] || status;
}

/**
 * Get emoji icon for file type
 */
export function getFileIcon(fileType) {
  const map = { pdf: "📄", audio: "🎵", video: "🎬" };
  return map[fileType] || "📎";
}

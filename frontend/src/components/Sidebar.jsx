import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import useStore from "../store/useStore";
import styles from "./Sidebar.module.css";

const FILE_ICONS = { pdf: "📄", audio: "🎵", video: "🎬" };
const STATUS_LABEL = {
  pending: { label: "Queued", cls: "pending" },
  processing: { label: "Processing…", cls: "processing" },
  ready: { label: "Ready", cls: "ready" },
  failed: { label: "Failed", cls: "failed" },
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Sidebar() {
  const {
    user, logout,
    documents, documentsLoading,
    uploadDocument, deleteDocument,
    activeDocument, setActiveDocument,
    fetchDocuments,
  } = useStore();

  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError] = useState("");

  // Poll status of processing docs
  React.useEffect(() => {
    const processingDocs = documents.filter((d) => d.status === "processing" || d.status === "pending");
    if (processingDocs.length === 0) return;
    const timer = setInterval(() => fetchDocuments(), 4000);
    return () => clearInterval(timer);
  }, [documents, fetchDocuments]);

  const onDrop = useCallback(
    async (accepted) => {
      if (!accepted.length) return;
      const file = accepted[0];
      setUploading(true);
      setError("");
      try {
        const doc = await uploadDocument(file, file.name, setUploadPct);
        setActiveDocument(doc);
      } catch (e) {
        setError(e.response?.data?.error || e.response?.data?.file?.[0] || "Upload failed");
      } finally {
        setUploading(false);
        setUploadPct(0);
      }
    },
    [uploadDocument, setActiveDocument]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "audio/*": [".mp3", ".wav", ".m4a"],
      "video/*": [".mp4", ".webm"],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Delete this file?")) return;
    await deleteDocument(id);
  };

  return (
    <aside className={styles.sidebar}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandIcon}>◈</span>
          <span className={styles.brandName}>DocMind</span>
        </div>
        <div className={styles.userRow}>
          <span className={styles.username}>{user?.username}</span>
          <button onClick={logout} className={styles.logoutBtn} title="Sign out">
            ⎋
          </button>
        </div>
      </div>

      {/* Upload zone */}
      <div
        {...getRootProps()}
        className={`${styles.dropzone} ${isDragActive ? styles.dragActive : ""} ${uploading ? styles.uploading : ""}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className={styles.uploadProgress}>
            <div className={styles.progressBar}>
              <div className={styles.progressFill} style={{ width: `${uploadPct}%` }} />
            </div>
            <span>{uploadPct}%</span>
          </div>
        ) : (
          <>
            <span className={styles.dropIcon}>↑</span>
            <span className={styles.dropText}>
              {isDragActive ? "Drop it here" : "Upload PDF, Audio, or Video"}
            </span>
          </>
        )}
      </div>

      {error && <p className={styles.uploadError}>{error}</p>}

      {/* Document list */}
      <div className={styles.listHeader}>
        <span>Your files</span>
        <span className={styles.count}>{documents.length}</span>
      </div>

      <ul className={styles.list}>
        {documentsLoading && documents.length === 0 && (
          <li className={styles.loadingItem}>Loading…</li>
        )}
        {documents.map((doc) => {
          const isActive = activeDocument?.id === doc.id;
          const st = STATUS_LABEL[doc.status] || STATUS_LABEL.pending;
          return (
            <li
              key={doc.id}
              className={`${styles.docItem} ${isActive ? styles.active : ""}`}
              onClick={() => setActiveDocument(doc)}
            >
              <span className={styles.docIcon}>{FILE_ICONS[doc.file_type] || "📎"}</span>
              <div className={styles.docInfo}>
                <span className={styles.docTitle}>{doc.title}</span>
                <div className={styles.docMeta}>
                  <span className={`${styles.statusBadge} ${styles[st.cls]}`}>{st.label}</span>
                  <span className={styles.docSize}>{formatSize(doc.file_size)}</span>
                </div>
              </div>
              <button
                className={styles.deleteBtn}
                onClick={(e) => handleDelete(e, doc.id)}
                title="Delete"
              >
                ×
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

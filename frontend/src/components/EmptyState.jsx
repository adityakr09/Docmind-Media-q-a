import React from "react";
import styles from "./EmptyState.module.css";

export default function EmptyState() {
  return (
    <div className={styles.wrap}>
      <div className={styles.icon}>◈</div>
      <h2 className={styles.title}>Select or upload a file</h2>
      <p className={styles.sub}>
        Upload a PDF, audio, or video file from the sidebar to start asking questions.
      </p>
      <div className={styles.capabilities}>
        <div className={styles.cap}>
          <span>📄</span>
          <div>
            <strong>PDF Documents</strong>
            <p>Ask questions, get source page references</p>
          </div>
        </div>
        <div className={styles.cap}>
          <span>🎵</span>
          <div>
            <strong>Audio Files</strong>
            <p>Transcribe, Q&A, jump to timestamps</p>
          </div>
        </div>
        <div className={styles.cap}>
          <span>🎬</span>
          <div>
            <strong>Video Files</strong>
            <p>Transcribe, Q&A, play relevant moments</p>
          </div>
        </div>
      </div>
    </div>
  );
}

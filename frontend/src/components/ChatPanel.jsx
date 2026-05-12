import React, { useState, useEffect, useRef } from "react";
import useStore from "../store/useStore";
import { timestampAPI } from "../services/api";
import styles from "./ChatPanel.module.css";

function formatTime(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function SourceBadge({ sources, fileType }) {
  if (!sources || sources.length === 0) return null;
  if (fileType === "pdf") {
    const pages = [...new Set(sources.filter(Boolean))];
    if (!pages.length) return null;
    return (
      <div className={styles.sources}>
        {pages.map((p) => (
          <span key={p} className={styles.sourceBadge}>p. {p}</span>
        ))}
      </div>
    );
  }
  const ts = sources.filter((s) => s?.start != null);
  if (!ts.length) return null;
  return (
    <div className={styles.sources}>
      {ts.map((t, i) => (
        <span key={i} className={`${styles.sourceBadge} ${styles.tsBadge}`}>
          {formatTime(t.start)}–{formatTime(t.end)}
        </span>
      ))}
    </div>
  );
}

export default function ChatPanel() {
  const { activeDocument, messages, chatLoading, fetchHistory, askQuestion, clearChat, refreshDocument } =
    useStore();

  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [topicSearch, setTopicSearch] = useState("");
  const [timestamps, setTimestamps] = useState([]);
  const [tsLoading, setTsLoading] = useState(false);
  const [currentTab, setCurrentTab] = useState("chat"); // 'chat' | 'summary' | 'timestamps'
  const [mediaTime, setMediaTime] = useState(null);

  const bottomRef = useRef(null);
  const mediaRef = useRef(null);
  const inputRef = useRef(null);
  const doc = activeDocument;
  const isMedia = doc?.file_type === "audio" || doc?.file_type === "video";

  useEffect(() => {
    if (doc?.id) {
      fetchHistory(doc.id);
      setCurrentTab("chat");
      setTimestamps([]);
      setTopicSearch("");
      setError("");
    }
  }, [doc?.id, fetchHistory]);

  // Poll until ready
  useEffect(() => {
    if (doc?.status === "processing" || doc?.status === "pending") {
      const t = setInterval(() => refreshDocument(doc.id), 3000);
      return () => clearInterval(t);
    }
  }, [doc?.status, doc?.id, refreshDocument]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  // Seek media player
  useEffect(() => {
    if (mediaTime !== null && mediaRef.current) {
      mediaRef.current.currentTime = mediaTime;
      mediaRef.current.play().catch(() => {});
    }
  }, [mediaTime]);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || chatLoading) return;
    if (doc.status !== "ready") {
      setError("Document is still processing. Please wait.");
      return;
    }
    const q = question;
    setQuestion("");
    setError("");
    try {
      await askQuestion(doc.id, q);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to get answer");
    }
  };

  const handleTimestampSearch = async (e) => {
    e.preventDefault();
    if (!topicSearch.trim()) return;
    setTsLoading(true);
    try {
      const { data } = await timestampAPI.search(doc.id, topicSearch);
      setTimestamps(data);
    } catch {
      setTimestamps([]);
    } finally {
      setTsLoading(false);
    }
  };

  const mediaUrl = doc?.file
    ? `http://localhost:8000/media/${doc.file.split("/media/")[1] || doc.file}`
    : null;

  if (!doc) return null;

  return (
    <div className={styles.panel}>
      {/* Doc header */}
      <div className={styles.docHeader}>
        <div className={styles.docMeta}>
          <span className={styles.docType}>
            {doc.file_type === "pdf" ? "📄" : doc.file_type === "audio" ? "🎵" : "🎬"}
          </span>
          <div>
            <h2 className={styles.docTitle}>{doc.title}</h2>
            <span className={`${styles.statusPill} ${styles[doc.status]}`}>
              {doc.status === "ready"
                ? "Ready"
                : doc.status === "processing"
                ? "Processing…"
                : doc.status === "pending"
                ? "Queued"
                : "Failed"}
            </span>
          </div>
        </div>
        <div className={styles.tabs}>
          {["chat", "summary", ...(isMedia ? ["timestamps"] : [])].map((tab) => (
            <button
              key={tab}
              className={`${styles.tab} ${currentTab === tab ? styles.tabActive : ""}`}
              onClick={() => setCurrentTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Media player */}
      {isMedia && doc.status === "ready" && mediaUrl && (
        <div className={styles.mediaBar}>
          {doc.file_type === "video" ? (
            <video
              ref={mediaRef}
              src={mediaUrl}
              controls
              className={styles.videoPlayer}
            />
          ) : (
            <audio ref={mediaRef} src={mediaUrl} controls className={styles.audioPlayer} />
          )}
        </div>
      )}

      {/* Processing state */}
      {(doc.status === "processing" || doc.status === "pending") && (
        <div className={styles.processingBanner}>
          <span className={styles.spinner} />
          <span>Extracting and indexing content — this takes a moment…</span>
        </div>
      )}

      {/* TAB: Chat */}
      {currentTab === "chat" && (
        <>
          <div className={styles.messages}>
            {messages.length === 0 && doc.status === "ready" && (
              <div className={styles.emptyChatHint}>
                <p>Ask anything about <strong>{doc.title}</strong></p>
                <div className={styles.suggestions}>
                  {["Summarize the main points", "What are the key topics?", "Explain the introduction"].map((s) => (
                    <button key={s} className={styles.suggestionBtn} onClick={() => setQuestion(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`${styles.message} ${msg.role === "user" ? styles.userMsg : styles.assistantMsg}`}
              >
                <div className={styles.bubble}>
                  <p>{msg.content}</p>
                  {msg.role === "assistant" && (
                    <SourceBadge
                      sources={
                        doc.file_type === "pdf" ? msg.source_pages : msg.source_timestamps
                      }
                      fileType={doc.file_type}
                    />
                  )}
                  {msg.role === "assistant" && msg.source_timestamps?.length > 0 && (
                    <div className={styles.playButtons}>
                      {msg.source_timestamps.map((ts, i) => (
                        <button
                          key={i}
                          className={styles.playBtn}
                          onClick={() => {
                            setMediaTime(ts.start);
                            setCurrentTab("chat");
                          }}
                        >
                          ▶ {formatTime(ts.start)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className={`${styles.message} ${styles.assistantMsg}`}>
                <div className={`${styles.bubble} ${styles.thinkingBubble}`}>
                  <span className={styles.dot} />
                  <span className={styles.dot} />
                  <span className={styles.dot} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {error && <p className={styles.chatError}>{error}</p>}

          <form onSubmit={handleAsk} className={styles.inputRow}>
            <input
              ref={inputRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                doc.status === "ready"
                  ? "Ask a question about this file…"
                  : "Processing… please wait"
              }
              disabled={chatLoading || doc.status !== "ready"}
              className={styles.input}
            />
            <button
              type="submit"
              disabled={chatLoading || !question.trim() || doc.status !== "ready"}
              className={styles.sendBtn}
            >
              ↑
            </button>
          </form>

          {messages.length > 0 && (
            <div className={styles.clearRow}>
              <button className={styles.clearBtn} onClick={() => clearChat(doc.id)}>
                Clear chat
              </button>
            </div>
          )}
        </>
      )}

      {/* TAB: Summary */}
      {currentTab === "summary" && (
        <div className={styles.summaryPanel}>
          {doc.summary ? (
            <p className={styles.summaryText}>{doc.summary}</p>
          ) : (
            <p className={styles.noContent}>
              {doc.status === "ready" ? "No summary available." : "Summary will appear once processing is complete."}
            </p>
          )}
        </div>
      )}

      {/* TAB: Timestamps */}
      {currentTab === "timestamps" && isMedia && (
        <div className={styles.timestampPanel}>
          <form onSubmit={handleTimestampSearch} className={styles.topicForm}>
            <input
              value={topicSearch}
              onChange={(e) => setTopicSearch(e.target.value)}
              placeholder="Search a topic (e.g. 'introduction', 'conclusion')"
              className={styles.topicInput}
            />
            <button type="submit" className={styles.topicBtn} disabled={tsLoading}>
              {tsLoading ? "…" : "Find"}
            </button>
          </form>

          {timestamps.length > 0 ? (
            <ul className={styles.tsList}>
              {timestamps.map((ts, i) => (
                <li key={i} className={styles.tsItem}>
                  <div className={styles.tsTime}>
                    <button
                      className={styles.tsPlayBtn}
                      onClick={() => setMediaTime(ts.start || ts.start_seconds)}
                    >
                      ▶ {formatTime(ts.start || ts.start_seconds)}
                    </button>
                    <span className={styles.tsEnd}>
                      → {formatTime(ts.end || ts.end_seconds)}
                    </span>
                  </div>
                  <p className={styles.tsText}>{ts.text || ts.text_snippet}</p>
                  {ts.relevance_note && (
                    <p className={styles.tsNote}>{ts.relevance_note}</p>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            !tsLoading && (
              <p className={styles.noContent}>
                {topicSearch ? "No matching segments found." : "Enter a topic to find relevant moments."}
              </p>
            )
          )}
        </div>
      )}
    </div>
  );
}

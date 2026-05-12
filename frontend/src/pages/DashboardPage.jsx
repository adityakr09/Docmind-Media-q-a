import React, { useEffect } from "react";
import useStore from "../store/useStore";
import Sidebar from "../components/Sidebar";
import ChatPanel from "../components/ChatPanel";
import EmptyState from "../components/EmptyState";
import styles from "./Dashboard.module.css";

export default function DashboardPage() {
  const { fetchDocuments, activeDocument } = useStore();

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return (
    <div className={styles.layout}>
      <Sidebar />
      <main className={styles.main}>
        {activeDocument ? <ChatPanel /> : <EmptyState />}
      </main>
    </div>
  );
}

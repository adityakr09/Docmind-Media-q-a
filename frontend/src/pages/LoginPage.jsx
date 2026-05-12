import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import useStore from "../store/useStore";
import styles from "./Auth.module.css";

export default function LoginPage() {
  const [form, setForm] = useState({ username: "", password: "" });
  const { login, authLoading, authError } = useStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ok = await login(form.username, form.password);
    if (ok) navigate("/");
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>◈</span>
          <span className={styles.logoText}>DocMind</span>
        </div>
        <h1 className={styles.title}>Welcome back</h1>
        <p className={styles.sub}>Sign in to your workspace</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label>Username</label>
            <input
              type="text"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              placeholder="your_username"
              required
            />
          </div>
          <div className={styles.field}>
            <label>Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="••••••••"
              required
            />
          </div>
          {authError && <p className={styles.error}>{authError}</p>}
          <button type="submit" className={styles.btn} disabled={authLoading}>
            {authLoading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className={styles.link}>
          No account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}

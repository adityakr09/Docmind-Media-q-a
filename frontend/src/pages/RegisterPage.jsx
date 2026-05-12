import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import useStore from "../store/useStore";
import styles from "./Auth.module.css";

export default function RegisterPage() {
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const { register, authLoading, authError } = useStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ok = await register(form.username, form.email, form.password);
    if (ok) navigate("/");
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>◈</span>
          <span className={styles.logoText}>DocMind</span>
        </div>
        <h1 className={styles.title}>Create account</h1>
        <p className={styles.sub}>Start asking questions from your files</p>

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
            <label>Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@example.com"
            />
          </div>
          <div className={styles.field}>
            <label>Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="min 8 characters"
              required
            />
          </div>
          {authError && <p className={styles.error}>{authError}</p>}
          <button type="submit" className={styles.btn} disabled={authLoading}>
            {authLoading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className={styles.link}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

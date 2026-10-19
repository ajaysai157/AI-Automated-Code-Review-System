
import { useEffect, useState } from "react";
import {
  ShieldCheck,
  GitPullRequest,
  History,
  LogOut,
  ArrowUpRight,
  AlertTriangle,
  CheckCircle2,
  LoaderCircle,
  Code2,
  ChevronRight,
  Bug,
  LockKeyhole,
} from "lucide-react";
import api from "./api/axios";
import "./App.css";

function getError(error) {
  const data = error.response?.data;

  if (!data) return "Unable to connect to the backend. Check that Django is running.";

  if (typeof data.error === "string") return data.error;
  if (typeof data.detail === "string") return data.detail;

  const first = Object.values(data).flat(Infinity).find(
    (value) => typeof value === "string"
  );

  return first || "Something went wrong. Please try again.";
}

function App() {
  const [accessToken, setAccessToken] = useState(
    () => localStorage.getItem("accessToken")
  );
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    username: "",
    email: "",
    password: "",
  });
  const [prUrl, setPrUrl] = useState("");
  const [history, setHistory] = useState([]);
  const [currentReview, setCurrentReview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [view, setView] = useState("new");

  const authenticated = Boolean(accessToken);

  async function loadHistory() {
    if (historyLoading) return;
    setHistoryLoading(true);
    setError("");

    try {
      const response = await api.get("reviews/");
      setHistory(response.data);
    } catch (err) {
      setError(getError(err));
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    if (authenticated) {
      void (async () => {
        try {
          if (historyLoading) return;
          setHistoryLoading(true);
          setError("");
          const response = await api.get("reviews/");
          if (mounted) {
            setHistory(response.data);
          }
        } catch (err) {
          if (mounted) {
            setError(getError(err));
          }
        } finally {
          if (mounted) {
            setHistoryLoading(false);
          }
        }
      })();
    }
    return () => {
      mounted = false;
    };
  }, [authenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAuth(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);

    try {
      if (authMode === "register") {
        await api.post("register/", authForm);
        setAuthMode("login");
        setAuthForm((previous) => ({
          ...previous,
          password: "",
        }));
        setNotice("Account created. Sign in to continue.");
      } else {
        const response = await api.post("login/", {
          username: authForm.username,
          password: authForm.password,
        });

        localStorage.setItem("accessToken", response.data.access);
        localStorage.setItem("refreshToken", response.data.refresh);
        setAccessToken(response.data.access);
        setAuthForm({ username: "", email: "", password: "" });
      }
    } catch (err) {
      setError(getError(err));
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    setAccessToken(null);
    setHistory([]);
    setCurrentReview(null);
    setPrUrl("");
    setError("");
    setNotice("");
    setView("new");
    setHistoryLoading(false);
  }

  async function submitReview(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setCurrentReview(null);
    setLoading(true);

    try {
      const response = await api.post("review/", { pr_url: prUrl });
      setCurrentReview(response.data);
      setNotice("Pull request review completed.");
      await loadHistory();
    } catch (err) {
      setError(getError(err));
    } finally {
      setLoading(false);
    }
  }

  async function openReview(runId) {
    setError("");
    setNotice("");
    setLoading(true);

    try {
      const response = await api.get(`reviews/${runId}/`);
      setCurrentReview(response.data);
    } catch (err) {
      setError(getError(err));
    } finally {
      setLoading(false);
    }
  }

  const findings = currentReview?.findings || [];
  const severityCounts = {
    critical: findings.filter((f) => f.severity === "critical").length,
    high: findings.filter((f) => f.severity === "high").length,
    medium: findings.filter((f) => f.severity === "medium").length,
    low: findings.filter((f) => f.severity === "low").length,
  };

  if (!authenticated) {
    return (
      <main className="auth-layout">
        <section className="auth-brand">
          <div className="brand-mark">
            <ShieldCheck size={22} aria-hidden="true" />
          </div>
          <div>
            <p className="eyebrow">AI AUTOMATED CODE REVIEW</p>
            <h1>Ship secure code with confidence.</h1>
            <p className="auth-description">
              CodeSentry helps engineering teams review GitHub pull requests with AI-assisted findings,
              prioritized severities, and a searchable audit trail.
            </p>
            <div className="auth-features">
              <div className="auth-feature">
                <Code2 size={18} aria-hidden="true" />
                <span>Context-aware PR analysis across changed files</span>
              </div>
              <div className="auth-feature">
                <Bug size={18} aria-hidden="true" />
                <span>Prioritized findings with severity and confidence</span>
              </div>
              <div className="auth-feature">
                <History size={18} aria-hidden="true" />
                <span>Review history and detailed findings at your fingertips</span>
              </div>
            </div>
          </div>
          <p className="auth-footnote">AI findings are advisory. Always verify critical changes.</p>
        </section>

        <section className="auth-panel">
          <div className="auth-card">
            <div className="mobile-brand">
              <div className="brand-mark">
                <ShieldCheck size={20} aria-hidden="true" />
              </div>
              <span>CodeSentry</span>
            </div>
            <p className="eyebrow">{authMode === "login" ? "WELCOME BACK" : "GET STARTED"}</p>
            <h2>{authMode === "login" ? "Sign in to CodeSentry" : "Create your account"}</h2>
            <p className="muted">
              {authMode === "login"
                ? "Continue reviewing pull requests with a secure session."
                : "Create an account to start analyzing GitHub pull requests."}
            </p>

            {error && (
              <div className="alert error-alert" role="alert" aria-live="polite">
                <AlertTriangle size={18} aria-hidden="true" />
                <div>{error}</div>
                <button type="button" className="alert-dismiss" onClick={() => setError("")} aria-label="Dismiss error">
                  ×
                </button>
              </div>
            )}
            {notice && (
              <div className="alert success-alert" role="status" aria-live="polite">
                <CheckCircle2 size={18} aria-hidden="true" />
                <div>{notice}</div>
                <button type="button" className="alert-dismiss" onClick={() => setNotice("")} aria-label="Dismiss notice">
                  ×
                </button>
              </div>
            )}

            <form onSubmit={handleAuth} className="form-stack" noValidate>
              <label>
                Username
                <input
                  value={authForm.username}
                  onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                  placeholder="Your username"
                  autoComplete="username"
                  required
                />
              </label>

              {authMode === "register" && (
                <label>
                  Email address
                  <input
                    type="email"
                    value={authForm.email}
                    onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                    placeholder="you@example.com"
                    autoComplete="email"
                    required
                  />
                </label>
              )}

              <label>
                Password
                <input
                  type="password"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                  placeholder={authMode === "register" ? "At least 8 characters" : "Enter your password"}
                  autoComplete={authMode === "login" ? "current-password" : "new-password"}
                  minLength={authMode === "register" ? 8 : undefined}
                  required
                />
              </label>

              <button type="submit" className="primary-button button-base full-button" disabled={loading}>
                {loading ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <LockKeyhole size={18} aria-hidden="true" />}
                <span>{authMode === "login" ? "Sign in" : "Create account"}</span>
              </button>
            </form>

            <div className="switch-auth">
              <span>{authMode === "login" ? "New to CodeSentry?" : "Already have an account?"}</span>
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  setAuthMode(authMode === "login" ? "register" : "login");
                  setError("");
                  setNotice("");
                }}
              >
                {authMode === "login" ? "Create account" : "Sign in"}
              </button>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={() => setCurrentReview(null)}>
          <span className="brand-mark">
            <ShieldCheck size={20} aria-hidden="true" />
          </span>
          <span>
            CodeSentry
            <small>AI AUTOMATED CODE REVIEW</small>
          </span>
        </button>

        <p className="nav-caption">WORKSPACE</p>
        <button
          className={`nav-item ${(!currentReview && view === "new") ? "active" : ""}`}
          onClick={() => {
            setCurrentReview(null);
            setView("new");
            setError("");
            setNotice("");
          }}
        >
          <GitPullRequest size={18} aria-hidden="true" /> New review
        </button>
        <button
          className={`nav-item ${view === "history" ? "active" : ""}`}
          onClick={() => {
            setCurrentReview(null);
            setView("history");
            setError("");
            setNotice("");
            void loadHistory();
          }}
        >
          <History size={18} aria-hidden="true" /> Review history
        </button>

        <div className="sidebar-bottom">
          <div className="security-note">
            <ShieldCheck size={18} aria-hidden="true" />
            <div>
              <strong>Review responsibly</strong>
              <p>AI findings are advisory. Always verify critical changes.</p>
            </div>
          </div>
          <button className="nav-item logout-button" onClick={logout}>
            <LogOut size={18} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} aria-hidden="true" /> Code review
          </div>
          <div className="connection-status">
            <span aria-hidden="true" /> Authenticated session
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">AI-POWERED CODE ANALYSIS</p>
              <h1>{currentReview ? "Review findings" : "Pull request review"}</h1>
              <p className="muted">
                {currentReview
                  ? "Inspect prioritized findings with file, line, agent, and confidence to decide what needs attention."
                  : "Paste a public GitHub pull request URL to run an automated AI security and code review."}
              </p>
            </div>
            <div className="heading-icon">
              <Code2 size={22} aria-hidden="true" />
            </div>
          </div>

          {error && (
            <div className="alert error-alert" role="alert" aria-live="polite">
              <AlertTriangle size={18} aria-hidden="true" />
              <div>{error}</div>
              <button type="button" className="alert-dismiss" onClick={() => setError("")} aria-label="Dismiss error">
                ×
              </button>
            </div>
          )}
          {notice && (
            <div className="alert success-alert" role="status" aria-live="polite">
              <CheckCircle2 size={18} aria-hidden="true" />
              <div>{notice}</div>
              <button type="button" className="alert-dismiss" onClick={() => setNotice("")} aria-label="Dismiss notice">
                ×
              </button>
            </div>
          )}

          {!currentReview && view === "new" && (
            <section className="review-form-card">
              <div className="section-title">
                <div className="section-icon">
                  <GitPullRequest size={18} aria-hidden="true" />
                </div>
                <div>
                  <h2>Analyze a pull request</h2>
                  <p>Enter the full URL of a public GitHub pull request to start the review.</p>
                </div>
              </div>
              <form className="pr-form" onSubmit={submitReview}>
                <label htmlFor="pr-url">GitHub pull request URL</label>
                <div className="url-input-row">
                  <input
                    id="pr-url"
                    type="url"
                    value={prUrl}
                    onChange={(e) => setPrUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository/pull/123"
                    required
                  />
                  <button type="submit" className="primary-button button-base" disabled={loading}>
                    {loading ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <ArrowUpRight size={18} aria-hidden="true" />}
                    <span>{loading ? "Analyzing..." : "Run review"}</span>
                  </button>
                </div>
                <p className="field-hint">Use a valid HTTPS GitHub pull request URL.</p>
              </form>
            </section>
          )}

          {currentReview && (
            <section className="results-section">
              <div className="result-meta">
                <div>
                  <span className={`status-pill ${currentReview.aiReviewStatus === "completed" ? "status-good" : "status-warning"}`}>
                    {currentReview.aiReviewStatus?.replaceAll("_", " ")}
                  </span>
                  <a className="pr-link" href={currentReview.prUrl || prUrl} target="_blank" rel="noreferrer">
                    {currentReview.prUrl || prUrl} <ArrowUpRight size={14} aria-hidden="true" />
                  </a>
                </div>
                <button type="button" className="secondary-button button-base" onClick={() => { setCurrentReview(null); setView("new"); }}>
                  New review
                </button>
              </div>

              <div className="stats-grid">
                {[
                  ["Critical", severityCounts.critical, "critical"],
                  ["High", severityCounts.high, "high"],
                  ["Medium", severityCounts.medium, "medium"],
                  ["Low", severityCounts.low, "low"],
                ].map(([label, count, severity]) => (
                  <div className="stat-card" key={severity}>
                    <span className={`severity-dot ${severity}`} aria-hidden="true" />
                    <span className="stat-label">{label}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>

              <div className="findings-heading">
                <div><h2>Findings</h2><p>{findings.length} issue{findings.length === 1 ? "" : "s"} reported</p></div>
              </div>

              {findings.length === 0 ? (
                <div className="empty-state">
                  <CheckCircle2 size={32} aria-hidden="true" />
                  <h3>No findings returned</h3>
                  <p>The review returned no findings. This does not guarantee the code is free of issues.</p>
                </div>
              ) : (
                <div className="findings-list">
                  {findings.map((finding, index) => (
                    <article className="finding-card" key={`${finding.filePath}-${finding.line}-${index}`}>
                      <div className="finding-topline">
                        <span className={`severity-pill severity-${finding.severity}`}>
                          {finding.severity}
                        </span>
                        <span className="agent-label">{finding.agent} agent</span>
                        <span className="confidence">{Math.round((finding.confidence || 0) * 100)}% confidence</span>
                      </div>
                      <div className="file-location">
                      <Code2 size={14} aria-hidden="true" />
                      <code>{finding.filePath}</code>
                      {finding.line != null && <span>Line {finding.line}</span>}
                      </div>
                      <p className="finding-message">{finding.message}</p>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          {!currentReview && view === "history" && (
            <section className="history-section">
              <div className="section-title history-title">
                <div className="section-icon">
                  <History size={18} aria-hidden="true" />
                </div>
                <div>
                  <h2>Review history</h2>
                  <p>Your previously analyzed pull requests.</p>
                </div>
                <button type="button" className="refresh-button" onClick={() => void loadHistory()} title="Refresh history" aria-label="Refresh history">
                  <History size={16} aria-hidden="true" />
                </button>
              </div>

              {historyLoading ? (
                <div className="inline-loading">
                  <LoaderCircle className="spin" size={18} aria-hidden="true" /> Loading history...
                </div>
              ) : history.length === 0 ? (
                <div className="history-empty">
                  <div className="history-empty-icon">
                    <History size={18} aria-hidden="true" />
                  </div>
                  <div>No reviews yet</div>
                  <p className="muted">Your completed reviews will appear here.</p>
                </div>
              ) : (
                <div className="history-list">
                  {history.map((item) => (
                    <button
                      type="button"
                      className="history-row"
                      key={item.runId}
                      onClick={() => { openReview(item.runId); setView("new"); }}
                    >
                      <span className="history-repo-icon">
                        <GitPullRequest size={18} aria-hidden="true" />
                      </span>
                      <span className="history-details">
                        <strong>{item.prUrl}</strong>
                        <small>{new Date(item.createdAt).toLocaleString()}</small>
                      </span>
                      <span className={`status-pill ${item.aiReviewStatus === "completed" ? "status-good" : "status-warning"}`}>
                        {item.aiReviewStatus?.replaceAll("_", " ")}
                      </span>
                      <ChevronRight size={16} className="history-arrow" aria-hidden="true" />
                    </button>
                  ))}
                </div>
              )}
            </section>
          )}
           <footer className="app-footer">CodeSentry · AI-assisted code review. Human verification recommended.</footer>
        </div>
      </main>
    </div>
  );
}

export default App;

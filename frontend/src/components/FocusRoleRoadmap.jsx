import React, { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function FocusRoleRoadmap({ resumeId, roleSuggestions }) {
  const [selectedRole, setSelectedRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [roadmap, setRoadmap] = useState(null);

  const roleTitles = useMemo(
    () => (roleSuggestions || []).map((r) => r.title).filter(Boolean),
    [roleSuggestions]
  );

  if (!resumeId) return null;

  const getRoadmap = async () => {
    const role = selectedRole.trim();
    if (!role) {
      setError("Select or enter a role title.");
      return;
    }

    setLoading(true);
    setError("");
    setRoadmap(null);

    try {
      const res = await fetch(`${API_BASE}/learning-resources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_id: resumeId, role_titles: [role] }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to load roadmap.");
      setRoadmap(data?.focused_role_roadmap || null);
    } catch (e) {
      setError(e.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <h2>Focused Role Roadmap</h2>
      <p className="muted">Pick one role to get a step-by-step skill plan.</p>

      <div className="controls">
        {roleTitles.length > 0 ? (
          <select
            className="select"
            value=""
            onChange={(e) => {
              if (e.target.value) setSelectedRole(e.target.value);
            }}
          >
            <option value="">Suggested role...</option>
            {roleTitles.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        ) : null}

        <input
          className="input"
          type="text"
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          placeholder="Role title (e.g. Backend Engineer)"
        />
        <button className="btn-primary" type="button" disabled={loading} onClick={getRoadmap}>
          {loading ? "Loading..." : "Generate Roadmap"}
        </button>
      </div>

      {error ? <p className="error-msg">{error}</p> : null}

      {roadmap ? (
        <div className="subpanel">
          <h3>{roadmap.role}</h3>
          {roadmap.note ? <p className="muted">{roadmap.note}</p> : null}
          {roadmap.steps?.length ? (
            <ol className="list">
              {roadmap.steps.map((step, i) => (
                <li key={`${step.skill}-${i}`} className="list-item">
                  <strong>{step.skill}</strong> <span className="muted">({step.phase})</span>
                  {step.tip ? <p>{step.tip}</p> : null}
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

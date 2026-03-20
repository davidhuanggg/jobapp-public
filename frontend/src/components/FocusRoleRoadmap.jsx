import React, { useState } from "react";

export default function FocusRoleRoadmap({ resumeId, roleSuggestions }) {
  const [focusRole, setFocusRole] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!resumeId) return null;

  const titles = (roleSuggestions || []).map((r) => r.title).filter(Boolean);

  const loadRoadmap = async () => {
    const q = focusRole.trim();
    if (!q) {
      setError("Enter or pick a role title.");
      return;
    }
    setLoading(true);
    setError(null);
    setRoadmap(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/learning-resources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_id: resumeId, role_titles: [q] }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Could not load roadmap");
      }
      setRoadmap(data.focused_role_roadmap || null);
    } catch (e) {
      setError(e.message || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ marginTop: "1.5rem", maxWidth: 720 }}>
      <h2>Learning roadmap for one role</h2>
      <p style={{ color: "#444" }}>
        Pick a role you care about most. We request learning resources for that role only
        and return an ordered gap roadmap (foundation → next → stretch), using AI when
        available.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
        {titles.length > 0 && (
          <select
            value=""
            onChange={(e) => {
              if (e.target.value) setFocusRole(e.target.value);
            }}
            style={{ minWidth: 220 }}
          >
            <option value="">Suggested role…</option>
            {titles.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}
        <input
          type="text"
          placeholder="Role title (e.g. Backend Engineer)"
          value={focusRole}
          onChange={(e) => setFocusRole(e.target.value)}
          style={{ flex: "1 1 200px", minWidth: 180 }}
        />
        <button type="button" onClick={loadRoadmap} disabled={loading}>
          {loading ? "Loading…" : "Get roadmap"}
        </button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {roadmap && (
        <div style={{ marginTop: "1rem" }}>
          <h3>{roadmap.role}</h3>
          {roadmap.note && <p>{roadmap.note}</p>}
          {roadmap.steps && roadmap.steps.length > 0 ? (
            <ol>
              {roadmap.steps.map((s, i) => (
                <li key={i} style={{ marginBottom: "0.6rem" }}>
                  <strong>{s.skill}</strong>
                  <span style={{ color: "#666", marginLeft: 6 }}>({s.phase})</span>
                  {s.tip && (
                    <div style={{ fontSize: "0.95rem", color: "#333" }}>{s.tip}</div>
                  )}
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      )}
    </div>
  );
}

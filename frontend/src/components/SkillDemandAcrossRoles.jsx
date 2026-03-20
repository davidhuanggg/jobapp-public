import React from "react";

const emphasisStyle = {
  high: { background: "#1a5f1a", color: "#fff", padding: "2px 8px", borderRadius: 4 },
  medium: { background: "#b8860b", color: "#fff", padding: "2px 8px", borderRadius: 4 },
  low: { background: "#555", color: "#fff", padding: "2px 8px", borderRadius: 4 },
};

export default function SkillDemandAcrossRoles({ skillDemand }) {
  if (!skillDemand || !skillDemand.by_skill || skillDemand.by_skill.length === 0) {
    return null;
  }

  const yours = skillDemand.your_skills_in_demand || [];
  const focus = skillDemand.skills_to_focus_on || [];

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <h2>What to focus on learning</h2>
      <p style={{ maxWidth: 720 }}>
        We compare your resume to skills AI associates with each recommended role.{" "}
        <strong>Skills to focus on</strong> are gaps we see as especially useful across your list.{" "}
        <strong>High</strong> / <strong>medium</strong> / <strong>low</strong> = how broadly that
        skill shows up among your recommended roles (not a numeric score).
      </p>

      {focus.length > 0 ? (
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "1rem",
            border: "1px solid #2a6a2a",
            borderRadius: 8,
            background: "#f4fff4",
            maxWidth: 900,
          }}
        >
          <h3 style={{ marginTop: 0 }}>Recommended priorities (not on your resume yet)</h3>
          <ol>
            {focus.slice(0, 20).map((row, idx) => (
              <li key={idx} style={{ marginBottom: "0.65rem" }}>
                <strong>{row.skill}</strong>{" "}
                <span style={emphasisStyle[row.emphasis] || emphasisStyle.low}>
                  {row.emphasis} demand
                </span>
                <div style={{ fontSize: "0.95rem", color: "#333", marginTop: "0.2rem" }}>
                  {row.focus_note}
                </div>
                <div style={{ fontSize: "0.9rem", color: "#555" }}>
                  Roles: {row.roles.join(", ")}
                </div>
              </li>
            ))}
          </ol>
          {focus.length > 20 && (
            <p style={{ color: "#666", marginBottom: 0 }}>
              +{focus.length - 20} more gap skills — see full list below.
            </p>
          )}
        </div>
      ) : (
        <p style={{ maxWidth: 720, marginBottom: "1.25rem", color: "#333" }}>
          No cross-role gaps left for this set: your resume already includes every skill we saw
          across these recommended roles (at matching names). Check <strong>learning paths</strong>{" "}
          per role for anything still missing there.
        </p>
      )}

      {yours.length > 0 && (
        <div style={{ marginBottom: "1.25rem" }}>
          <h3>Strengths: your skills that show up across multiple recommended roles</h3>
          <ul>
            {yours.map((row, idx) => (
              <li key={idx} style={{ marginBottom: "0.35rem" }}>
                <strong>{row.skill}</strong>{" "}
                <span style={emphasisStyle[row.emphasis] || emphasisStyle.low}>
                  {row.emphasis}
                </span>
                {" — "}
                {row.roles.join(", ")}
              </li>
            ))}
          </ul>
        </div>
      )}

      <h3>Full skill demand across recommended roles</h3>
      <ul style={{ maxWidth: 900 }}>
        {skillDemand.by_skill.slice(0, 40).map((row, idx) => (
          <li key={idx} style={{ marginBottom: "0.5rem" }}>
            <strong>{row.skill}</strong>{" "}
            <span style={emphasisStyle[row.emphasis] || emphasisStyle.low}>
              {row.emphasis}
            </span>
            {" — "}
            {row.roles.join(", ")}
          </li>
        ))}
      </ul>
      {skillDemand.by_skill.length > 40 && (
        <p style={{ color: "#666" }}>
          Showing top 40 skills ({skillDemand.by_skill.length} total).
        </p>
      )}
    </div>
  );
}

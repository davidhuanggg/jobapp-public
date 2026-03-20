import React from "react";

const emphasisClass = {
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
};

export default function SkillDemandAcrossRoles({ skillDemand }) {
  if (!skillDemand?.by_skill?.length) return null;

  const toFocus = skillDemand.skills_to_focus_on || [];
  const strengths = skillDemand.your_skills_in_demand || [];

  return (
    <section className="panel">
      <h2>Priority Skills</h2>
      <p className="muted">High / medium / low indicates how broadly each skill appears across roles.</p>

      {toFocus.length > 0 ? (
        <div className="callout">
          <h3>Top Skills To Learn Next</h3>
          <ol className="list">
            {toFocus.slice(0, 15).map((item, i) => (
              <li key={`${item.skill}-${i}`} className="list-item">
                <div>
                  <strong>{item.skill}</strong>{" "}
                  <span className={`badge ${emphasisClass[item.emphasis] || "badge-low"}`}>
                    {item.emphasis}
                  </span>
                </div>
                <p>{item.focus_note}</p>
                <p className="muted">Roles: {item.roles?.join(", ")}</p>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <p className="muted">No high-priority gaps detected across the recommended roles.</p>
      )}

      {strengths.length > 0 ? (
        <>
          <h3>Your Reusable Strengths</h3>
          <ul className="list">
            {strengths.map((item, i) => (
              <li key={`${item.skill}-${i}`} className="list-item">
                <strong>{item.skill}</strong>{" "}
                <span className={`badge ${emphasisClass[item.emphasis] || "badge-low"}`}>
                  {item.emphasis}
                </span>
                <p className="muted">Roles: {item.roles?.join(", ")}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

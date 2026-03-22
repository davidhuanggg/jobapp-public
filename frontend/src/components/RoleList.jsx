import React from "react";

export default function RoleList({ roles }) {
  if (!roles?.length) return null;

  return (
    <section className="panel">
      <h2>Recommended Roles</h2>
      <p className="muted">Suggested from your resume profile (LLM + heuristics).</p>
      <ul className="list">
        {roles.map((role, i) => (
          <li key={`${role.title}-${i}`} className="list-item">
            <strong>{role.title}</strong>
            <p>{role.reason}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

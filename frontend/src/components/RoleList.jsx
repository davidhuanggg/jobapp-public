import React from "react";

export default function RoleList({ roles }) {
  if (!roles?.length) return null;

  return (
    <section className="panel">
      <h2>Recommended Roles</h2>
      <p className="muted">Based on your current resume profile.</p>
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

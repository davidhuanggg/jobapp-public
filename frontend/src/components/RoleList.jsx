import React from "react";

export default function RoleList({ roles }) {
  if (!roles || roles.length === 0) return null;

  return (
    <div>
      <h2>Recommended Roles</h2>
      <ul>
        {roles.map((role, idx) => (
          <li key={idx}>
            <strong>{role.title}</strong>: {role.reason}
          </li>
        ))}
      </ul>
    </div>
  );
}


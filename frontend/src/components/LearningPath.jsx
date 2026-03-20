import React from "react";

function SkillPills({ skills }) {
  if (!skills?.length) return <p className="muted">No items in this category.</p>;
  return (
    <ul className="pill-list">
      {skills.map((s, i) => (
        <li key={`${s}-${i}`} className="pill">
          {s}
        </li>
      ))}
    </ul>
  );
}

export default function LearningPath({ learningPaths }) {
  const entries = learningPaths && typeof learningPaths === "object" ? Object.entries(learningPaths) : [];
  if (!entries.length) return null;

  return (
    <section className="panel">
      <h2>Learning Paths By Role</h2>
      <p className="muted">Core skills first, then important, then optional.</p>

      <div className="stack">
        {entries.map(([role, buckets]) => (
          <article key={role} className="subpanel">
            <h3>{role}</h3>
            <div className="bucket">
              <h4>Core</h4>
              <SkillPills skills={buckets?.core || []} />
            </div>
            <div className="bucket">
              <h4>Important</h4>
              <SkillPills skills={buckets?.important || []} />
            </div>
            <div className="bucket">
              <h4>Optional</h4>
              <SkillPills skills={buckets?.optional || []} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

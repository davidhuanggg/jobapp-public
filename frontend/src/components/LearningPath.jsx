import React from "react";

export default function LearningPath({ learningPaths }) {
  if (!learningPaths) return null;

  // Backend returns learning_paths as an object: { [roleTitle]: [{skill, courses}, ...] }
  // Normalize it to an array for rendering.
  const items = Array.isArray(learningPaths)
    ? learningPaths
    : Object.values(learningPaths).flat();

  if (!items || items.length === 0) return null;

  return (
    <div>
      <h2>Learning Recommendations</h2>
      <ul>
        {items.map((item, idx) => (
          <li key={idx}>
            <strong>{item.skill}</strong>: {item.courses.join(", ")}
          </li>
        ))}
      </ul>
    </div>
  );
}


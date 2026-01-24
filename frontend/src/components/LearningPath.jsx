import React from "react";

export default function LearningPath({ learningPaths }) {
  if (!learningPaths || learningPaths.length === 0) return null;

  return (
    <div>
      <h2>Learning Recommendations</h2>
      <ul>
        {learningPaths.map((item, idx) => (
          <li key={idx}>
            <strong>{item.skill}</strong>: {item.courses.join(", ")}
          </li>
        ))}
      </ul>
    </div>
  );
}


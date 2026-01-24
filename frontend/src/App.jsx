import React, { useState } from "react";
import ResumeUpload from "./components/ResumeUpload";
import RoleList from "./components/RoleList";
import LearningPath from "./components/LearningPath";

export default function App() {
  const [parsedResume, setParsedResume] = useState(null);
  const [recommendedRoles, setRecommendedRoles] = useState([]);
  const [learningPaths, setLearningPaths] = useState([]);
  const [loadingRoles, setLoadingRoles] = useState(false);

  const handleResumeParsed = async (resume) => {
    setParsedResume(resume);
    setLoadingRoles(true);

    try {
      // Call backend to get recommended jobs
      const res = await fetch("http://127.0.0.1:8000/recommend-jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resume),
      });

      if (!res.ok) throw new Error("Failed to get recommended jobs");

      const data = await res.json();
      setRecommendedRoles(data.recommended_roles || []);
      setLearningPaths(data.learning_paths || []); // optional
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingRoles(false);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <ResumeUpload onResumeParsed={handleResumeParsed} />

      {loadingRoles && <p>Loading recommendations...</p>}

      <RoleList roles={recommendedRoles} />
      <LearningPath learningPaths={learningPaths} />
    </div>
  );
}


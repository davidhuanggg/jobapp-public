import React, { useState } from "react";
import ResumeUpload from "./components/ResumeUpload";
import RoleList from "./components/RoleList";
import LearningPath from "./components/LearningPath";

export default function App() {
  const [recommendedRoles, setRecommendedRoles] = useState([]);
  const [learningPaths, setLearningPaths] = useState([]);
  const [loadingRoles, setLoadingRoles] = useState(false);

  const handleResumeParsed = async (backendData) => {
    setLoadingRoles(true);

    try {
      setRecommendedRoles(backendData?.recommendations || []);
      setLearningPaths(backendData?.learning_paths || {});
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


import React, { useState } from "react";
import ResumeUpload from "./components/ResumeUpload";
import RoleList from "./components/RoleList";
import LearningPath from "./components/LearningPath";
import SkillDemandAcrossRoles from "./components/SkillDemandAcrossRoles";
import FocusRoleRoadmap from "./components/FocusRoleRoadmap";

export default function App() {
  const [recommendedRoles, setRecommendedRoles] = useState([]);
  const [learningPaths, setLearningPaths] = useState([]);
  const [skillDemand, setSkillDemand] = useState(null);
  const [resumeId, setResumeId] = useState(null);
  const [loadingRoles, setLoadingRoles] = useState(false);

  const handleResumeParsed = async (backendData) => {
    setLoadingRoles(true);

    try {
      setRecommendedRoles(backendData?.recommendations || []);
      setLearningPaths(backendData?.learning_paths || {});
      setSkillDemand(backendData?.skill_demand_across_recommended_roles || null);
      setResumeId(backendData?.resume_id ?? null);
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
      <SkillDemandAcrossRoles skillDemand={skillDemand} />
      <FocusRoleRoadmap resumeId={resumeId} roleSuggestions={recommendedRoles} />
      <LearningPath learningPaths={learningPaths} />
    </div>
  );
}


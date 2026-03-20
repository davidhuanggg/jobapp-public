import React, { useState } from "react";
import ResumeUpload from "./components/ResumeUpload";
import RoleList from "./components/RoleList";
import SkillDemandAcrossRoles from "./components/SkillDemandAcrossRoles";
import FocusRoleRoadmap from "./components/FocusRoleRoadmap";
import LearningPath from "./components/LearningPath";

export default function App() {
  const [resumeId, setResumeId] = useState(null);
  const [roles, setRoles] = useState([]);
  const [skillDemand, setSkillDemand] = useState(null);
  const [learningPaths, setLearningPaths] = useState({});
  const [loading, setLoading] = useState(false);

  const handleResumeParsed = (data) => {
    setLoading(true);
    try {
      setResumeId(data?.resume_id ?? null);
      setRoles(data?.recommendations ?? []);
      setSkillDemand(data?.skill_demand_across_recommended_roles ?? null);
      setLearningPaths(data?.learning_paths ?? {});
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="panel">
        <h1>Career Compass</h1>
        <p className="muted">
          Upload your resume to get suggested roles, priority skills, and a focused roadmap.
        </p>
        <ResumeUpload onResumeParsed={handleResumeParsed} />
      </section>

      {loading && <p className="loading-msg">Generating recommendations...</p>}

      <RoleList roles={roles} />
      <SkillDemandAcrossRoles skillDemand={skillDemand} />
      <FocusRoleRoadmap resumeId={resumeId} roleSuggestions={roles} />
      <LearningPath learningPaths={learningPaths} />
    </main>
  );
}

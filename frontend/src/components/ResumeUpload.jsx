import React, { useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function ResumeUpload({ onResumeParsed }) {
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) {
      setError("Please choose a PDF or DOCX resume first.");
      return;
    }

    setSubmitting(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/parse-and-recommend`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to parse resume.");
      onResumeParsed(data);
    } catch (e) {
      setError(e.message || "Request failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="upload-row">
      <input
        type="file"
        accept=".pdf,.doc,.docx"
        className="input-file"
        onChange={(e) => {
          setFile(e.target.files?.[0] || null);
          setError("");
        }}
      />
      <button className="btn-primary" type="button" onClick={handleUpload} disabled={submitting}>
        {submitting ? "Uploading..." : "Upload Resume"}
      </button>
      {error ? <p className="error-msg">{error}</p> : null}
    </div>
  );
}

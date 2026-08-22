import { useState, useEffect } from "react";
import { listJobs, createJob, getJob, deleteJob } from "./services/api";
import type { Job } from "./types/job";

function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [seconds, setSeconds] = useState("2");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  async function handleLoad() {
    try {
      setError(null);
      const data = await listJobs();
      setJobs(data);
      
      if (selectedId) {
        const updated = await getJob(selectedId);
        setSelectedJob(updated);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    handleLoad();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      setError(null);
      await createJob({
        name,
        payload: { seconds: Number(seconds) || 2 },
      });
      setName("");
      setSeconds("2");
      await handleLoad(); // refresh list
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create job");
    }
  }

  async function handleSelect(id: string) {
    setSelectedId(id);
    try {
      const job = await getJob(id);
      setSelectedJob(job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch job details");
    }
  }

  useEffect(() => {
    if (!selectedId) return;

    const intervalId = setInterval(async () => {
      try {
        const job = await getJob(selectedId);
        setSelectedJob(job);

        const updatedList = await listJobs();
        setJobs(updatedList);

        if (job.status !== "queued" && job.status !== "running") {
          clearInterval(intervalId);
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [selectedId]);

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation(); 
    try {
      setError(null);
      await deleteJob(id);
      if (selectedId === id) {
        setSelectedId(null);
        setSelectedJob(null);
      }
      await handleLoad();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete job");
    }
  }

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>TaskFlow</h1>
      
      <button type="button" onClick={handleLoad}>
        Manual Refresh
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Step 3: Create Form */}
      <section style={{ margin: "1rem 0", padding: "1rem", border: "1px solid #ccc" }}>
        <h2>Create New Job</h2>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: "1rem" }}>
          <input
            type="text"
            placeholder="Job Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            type="number"
            placeholder="Seconds"
            value={seconds}
            onChange={(e) => setSeconds(e.target.value)}
            required
          />
          <button type="submit">Submit</button>
        </form>
      </section>

      <div style={{ display: "flex", gap: "2rem" }}>
        {/* Job List */}
        <section style={{ flex: 1 }}>
          <h2>Jobs ({jobs.length})</h2>
          <ul>
            {jobs.map((job) => (
              <li
                key={job.id}
                onClick={() => handleSelect(job.id)}
                style={{
                  cursor: "pointer",
                  background: job.id === selectedId ? "#f0f0f0" : "transparent",
                  padding: "0.5rem",
                  marginBottom: "0.5rem",
                  border: "1px solid #ddd",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>
                  <strong>{job.name}</strong> — {job.status}
                </span>
                {(job.status === "queued") && (
                  <button onClick={(e) => handleDelete(job.id, e)}>Cancel</button>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section style={{ flex: 1, padding: "1rem", border: "1px solid #ccc" }}>
          <h2>Job Details</h2>
          {selectedJob ? (
            <div>
              <p><strong>ID:</strong> {selectedJob.id}</p>
              <p><strong>Name:</strong> {selectedJob.name}</p>
              <p><strong>Status:</strong> {selectedJob.status}</p>
              <p><strong>Result:</strong> {selectedJob.result ?? "N/A"}</p>
              <p><strong>Error:</strong> {selectedJob.error ?? "None"}</p>
              <p><strong>Created At:</strong> {selectedJob.created_at}</p>
              <p><strong>Started At:</strong> {selectedJob.started_at ?? "N/A"}</p>
              <p><strong>Completed At:</strong> {selectedJob.completed_at ?? "N/A"}</p>
            </div>
          ) : (
            <p>Select a job from the list to view details.</p>
          )}
        </section>
      </div>
    </main>
  );
}

export default App;
import type { JobCreate, Job } from "../types/job";

const API_BASE = "http://127.0.0.1:8000";

export async function listJobs(): Promise<Job[]> {
    const response = await fetch(`${API_BASE}/api/jobs`);
    
    if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`);
    }
    
    return response.json() as Promise<Job[]>;
}

export async function createJob(body: JobCreate): Promise<Job> {
    const response = await fetch(`${API_BASE}/api/jobs`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        throw new Error(`Failed to create job: ${response.statusText}`);
    }
    
    return response.json() as Promise<Job>;
}

export async function getJob(id: string): Promise<Job> {
    const response = await fetch(`${API_BASE}/api/jobs/${id}`);
    
    if (!response.ok) {
        throw new Error(`Failed to fetch job ${id}: ${response.statusText}`);
    }
    
    return response.json() as Promise<Job>;
}

export async function deleteJob(id: string): Promise<Job> {
    const response = await fetch(`${API_BASE}/api/jobs/${id}`, {
        method: "DELETE"});
    if (!response.ok) {
        throw new Error(`Failed to delete job ${id}: ${response.statusText}`);
    }
    
    return response.json() as Promise<Job>;
}
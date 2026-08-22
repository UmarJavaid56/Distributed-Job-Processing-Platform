export type JobStatus =
    | "queued"
    | "running"
    | "completed"
    | "failed"
    | "cancelled";

export interface Job
{
    id: string;
    name: string;
    payload: Record<string, unknown>;
    status: JobStatus;
    result: string | null;
    error: string | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
}

export interface JobCreate
{
    name: string;
    payload: Record<string, unknown>
}